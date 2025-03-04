import discord, os, aiosqlite
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

    @discord.ui.button(label="Opt-In", style=discord.ButtonStyle.green, custom_id="meeting_optin")
    async def opt_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.add_roles(self.meeting_role)
            await interaction.response.send_message("You have been opted in for the meeting!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error signing up: {e}", ephemeral=True)

    @discord.ui.button(label="Opt-Out", style=discord.ButtonStyle.red, custom_id="meeting_optout")
    async def opt_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.remove_roles(self.meeting_role)
            await interaction.response.send_message("You have been opted out of the meeting.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error opting out: {e}", ephemeral=True)


class MeetingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="create_meeting",
        description="Creates a meeting and logs it to the database.",
    )
    @app_commands.describe(
        title="The title for the meeting",
        description="Description of the meeting",
        time="Meeting time in 12-hour format (e.g., 3:00 PM)",
        date="Meeting date in MM/DD/YYYY format",
    )
    @app_commands.guilds(GUILD_ID)
    async def create_meeting(self, interaction: discord.Interaction, title: str, description: str, time: str, date: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        meetings_category = discord.utils.get(guild.categories, name="Meetings")
        if meetings_category is None:
            return await interaction.response.send_message("The 'Meetings' category does not exist.", ephemeral=True)

        meeting_list_forum = discord.utils.get(meetings_category.channels, name="meeting-list", type=discord.ChannelType.forum)
        if meeting_list_forum is None:
            return await interaction.response.send_message("The 'meeting-list' forum channel does not exist.", ephemeral=True)

        meeting_datetime = f"{date} {time}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO meetings (name, description, host_id, date_time, created_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, description, interaction.user.id, meeting_datetime, now, now, "scheduled")
            )
            await db.commit()
            meeting_db_id = cursor.lastrowid

        meeting_role = await guild.create_role(name=f"Meeting: {title}", reason="Created for meeting access")
        bot_role = discord.utils.get(guild.roles, name="Bot")
        if bot_role is None:
            return await interaction.response.send_message("Bot role not found.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            bot_role: discord.PermissionOverwrite(view_channel=True, move_members=True),
            meeting_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True),
        }

        meeting_text_channel = await guild.create_text_channel(name=f"{title.lower().replace(' ', '-')}-text", category=meetings_category, overwrites=overwrites)
        meeting_voice_channel = await guild.create_voice_channel(name=f"{title.lower().replace(' ', '-')}-voice", category=meetings_category, overwrites=overwrites)

        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("UPDATE meetings SET voice_channel_id = ? WHERE id = ?", (meeting_voice_channel.id, meeting_db_id))
            await db.commit()

        embed = discord.Embed(title=f"Meeting {title} Created!", description=f"\nMeeting ID: {meeting_db_id}\n{description}", color=discord.Color.blue())
        embed.add_field(name="Date & Time", value=meeting_datetime, inline=True)
        embed.add_field(name="Text Channel", value=meeting_text_channel.mention, inline=False)
        embed.add_field(name="Voice Channel", value=meeting_voice_channel.mention, inline=False)

        view = MeetingButtons(meeting_role)
        post_message = await meeting_list_forum.create_thread(name=title, embed=embed, view=view)

        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("UPDATE meetings SET thread_id = ? WHERE id = ?", (post_message.thread.id, meeting_db_id))
            await db.commit()

        await interaction.response.send_message("Meeting created successfully! Check the forum post for details.")


async def setup(bot: commands.Bot):
    await bot.add_cog(MeetingCog(bot))
