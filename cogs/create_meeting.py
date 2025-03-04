import os, sqlite3, discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# Load GUILD_ID from .env file
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))
DATABASE_PATH = "database.db"


class MeetingButtons(discord.ui.View):
    """
    A View that contains two buttons: Opt-In and Opt-Out.
    Users can click these buttons to be given or removed the meeting role.
    """

    def __init__(self, meeting_role: discord.Role):
        super().__init__(timeout=None)
        self.meeting_role = meeting_role

    # Add the meeting role to the user
    @discord.ui.button(
        label="Opt-In", style=discord.ButtonStyle.green, custom_id="meeting_optin"
    )
    async def opt_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.add_roles(self.meeting_role)
            await interaction.response.send_message(
                "You have been opted in for the meeting!", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error signing up: {e}", ephemeral=True
            )

    # Remove the meeting role from the user
    @discord.ui.button(
        label="Opt-Out", style=discord.ButtonStyle.red, custom_id="meeting_optout"
    )
    async def opt_out(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            await interaction.user.remove_roles(self.meeting_role)
            await interaction.response.send_message(
                "You have been opted out of the meeting.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error opting out: {e}", ephemeral=True
            )


class MeetingCog(commands.Cog):
    """Cog that provides a command to create a meeting."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="create_meeting",
        description="Creates a meeting using an existing category and forum channel, and logs it to the database.",
    )
    @app_commands.describe(
        title="The title for the meeting",
        description="Description of the meeting",
        time="Meeting time in 12-hour format (e.g., 3:00 PM)",
        date="Meeting date in MM/DD/YYYY format",
    )

    # Registers the command only for the specified guild for immediate availability.
    @app_commands.guilds(GUILD_ID)
    async def create_meeting(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        time: str,
        date: str,
    ):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )

        # 1. Find the "Meetings" category in the server.
        meetings_category = None
        for cat in guild.categories:
            if cat.name.lower() == "meetings":
                meetings_category = cat
                break
        if meetings_category is None:
            return await interaction.response.send_message(
                "The 'Meetings' category does not exist.", ephemeral=True
            )

        # 2. Locate the "meeting-list" forum channel within the "Meetings" category.
        meeting_list_forum = None
        for channel in guild.channels:
            if (
                channel.category_id == meetings_category.id
                and channel.name.lower() == "meeting-list"
            ):
                # Check if it's a forum channel
                if isinstance(channel, discord.ForumChannel):
                    meeting_list_forum = channel
                    break
        if meeting_list_forum is None:
            return await interaction.response.send_message(
                "The 'meeting-list' forum channel does not exist in the 'Meetings' category.",
                ephemeral=True,
            )

        # 3. Insert the new meeting record into the database to get a unique meeting ID.
        meeting_datetime = f"{date} {time}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            query = """
                INSERT INTO meetings 
                (name, description, host_id, date_time, duration, created_at, updated_at, status, voice_channel_id, thread_id, recurring_interval, recurring_end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            values = (
                title,
                description,
                interaction.user.id,
                meeting_datetime,
                None,
                now,
                now,
                "scheduled",
                None,
                None,
                None,
                None,
            )
            cursor.execute(query, values)
            conn.commit()

            meeting_db_id = cursor.lastrowid
            conn.close()
        except Exception as e:
            return await interaction.response.send_message(
                f"Error saving meeting to database: {e}", ephemeral=True
            )

        # 4. Create a meeting role with the name "Meeting: {meeting_db_id}"
        role_name = f"Meeting: {title}"
        try:
            meeting_role = await guild.create_role(
                name=role_name, reason="Created for meeting access"
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error creating meeting role: {e}", ephemeral=True
            )

        # 5. Create restricted text and voice channels (only visible to members with the meeting role).
        sanitized_meeting_title = title.lower().replace(" ", "-")
        bot_role = discord.utils.get(guild.roles, name="Bot")
        if bot_role is None:
            return await interaction.response.send_message(
                "Bot role not found in the server.", ephemeral=True
            )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_role: discord.PermissionOverwrite(view_channel=True, move_members=True),
            meeting_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, connect=True
            ),
        }
        try:
            meeting_text_channel = await guild.create_text_channel(
                name=f"{sanitized_meeting_title}-text",
                category=meetings_category,
                overwrites=overwrites,
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error creating meeting text channel: {e}", ephemeral=True
            )
        try:
            meeting_voice_channel = await guild.create_voice_channel(
                name=f"{sanitized_meeting_title}-voice",
                category=meetings_category,
                overwrites=overwrites,
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error creating meeting voice channel: {e}", ephemeral=True
            )

        # 6. Update the meeting record in the database with the voice channel ID.
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            update_query = """
                UPDATE meetings
                SET voice_channel_id = ?
                WHERE id = ?
            """
            cursor.execute(update_query, (meeting_voice_channel.id, meeting_db_id))
            conn.commit()
            conn.close()
        except Exception as e:
            return await interaction.response.send_message(
                f"Error updating meeting in database: {e}", ephemeral=True
            )

        # 7. Build an embed with the meeting details.
        embed = discord.Embed(
            title=f"Meeting {title} Created!",
            description=f"\nMeeting ID: {meeting_db_id}\n{description}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Date & Time", value=meeting_datetime, inline=True)
        embed.add_field(
            name="Text Channel", value=meeting_text_channel.mention, inline=False
        )
        embed.add_field(
            name="Voice Channel", value=meeting_voice_channel.mention, inline=False
        )

        # 8. Create a forum post in the "meeting-list" forum channel using the embed.
        try:
            view = MeetingButtons(meeting_role)
            post_message = await meeting_list_forum.create_thread(
                name=title, embed=embed, view=view
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"Error creating forum post: {e}", ephemeral=True
            )

        # 9. Update the meeting record in the database with the forum post (thread) ID.
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            update_query = """
                UPDATE meetings
                SET thread_id = ?
                WHERE id = ?
            """
            cursor.execute(update_query, (post_message.thread.id, meeting_db_id))
            conn.commit()
            conn.close()
        except Exception as e:
            return await interaction.response.send_message(
                f"Error updating meeting in database: {e}", ephemeral=True
            )

        # 10. Send final confirmation message.
        await interaction.response.send_message(
            "Meeting created successfully! Check the forum post for details.",
            ephemeral=False,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MeetingCog(bot))
