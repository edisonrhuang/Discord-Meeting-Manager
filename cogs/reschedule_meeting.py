import discord, os, aiosqlite
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import re

# Load GUILD_ID from .env file
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))
DATABASE_PATH = "database.db"

TIME_FORMATS = [
    r"^(1[0-2]|0?[1-9]):([0-5][0-9]) ?([APap][Mm])$",  # 12-hour format with AM/PM (e.g., "1:00 PM", "01:00pm")
    r"^(1[0-9]|2[0-3]|0?[0-9]):([0-5][0-9])$",  # 24-hour format (e.g., "13:00")
]

DATE_FORMATS = [
    r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/(\d{4})$",  # MM/DD/YYYY or M/D/YYYY
    r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/(\d{2})$",  # MM/DD/YY or M/D/YY
]

def parse_time(input_time: str) -> str:
    """Parses various time formats and returns a 24-hour format string (HH:MM)."""
    for pattern in TIME_FORMATS:
        match = re.match(pattern, input_time)
        if match:
            if len(match.groups()) == 3:  # 12-hour format
                hours, minutes, period = match.groups()
                hours = int(hours)
                if period.lower() == "pm" and hours != 12:
                    hours += 12
                elif period.lower() == "am" and hours == 12:
                    hours = 0
            else:  # 24-hour format
                hours, minutes = map(int, match.groups())

            return f"{hours:02}:{minutes:02}"  # Return HH:MM format

    raise ValueError(f"Invalid time format: {input_time}")

def parse_date(input_date: str) -> str:
    """Parses various date formats and returns MM/DD/YYYY format."""
    for pattern in DATE_FORMATS:
        match = re.match(pattern, input_date)
        if match:
            month, day, year = match.groups()
            year = int(year)
            if year < 100:  # Convert YY to YYYY (assuming 2000s)
                year += 2000
            return f"{year}-{int(month):02}-{int(day):02}"  # Return YYYY/MM/DD format

    raise ValueError(f"Invalid date format: {input_date}")

class MeetingButtons(discord.ui.View):
    """A View that contains two buttons: Opt-In and Opt-Out."""

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

class RescheduleMeetingCog(commands.Cog):
    """
    Cog to reschedule a meeting and notify participants.

    Users run /reschedule_meeting with:
     - meeting_id: the unique meeting ID in the database
     - new_time: new meeting time (or 'none' to keep current)
     - new_date: new meeting date (or 'none' to keep current)

    The command updates the meeting record, sends a notification in the meeting's text channel,
    and posts a new message in the forum thread with a new embed and interactive buttons.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="reschedule_meeting",
        description="Reschedules a meeting and notifies participants.",
    )
    @app_commands.describe(
        meeting_id="The unique meeting ID to reschedule",
        new_time="New meeting time (e.g., 1:00 PM, 13:00) or 'none' to keep current",
        new_date="New meeting date (e.g., M/D/YY, MM/DD/YYYY) or 'none' to keep current",
    )
    @app_commands.guilds(GUILD_ID)
    async def reschedule_meeting(self, interaction: discord.Interaction, meeting_id: int, new_time: str, new_date: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        # Fetch the meeting record by ID.
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT id, name, description, date_time, voice_channel_id, thread_id, role_id FROM meetings WHERE id = ?",
                (meeting_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return await interaction.response.send_message(f"Meeting with id: '{meeting_id}' not found.", ephemeral=True)

        mid, name, description, current_datetime_str, voice_channel_id, thread_id, role_id = row

        # Parse the current meeting datetime.
        current_dt = datetime.strptime(current_datetime_str, "%Y-%m-%d %H:%M:%S")

        # Determine new time and date values and check if they are 'none'.
        new_time_val = current_dt.strftime("%H:%M") if new_time.lower() == "none" else parse_time(new_time)
        new_date_val = current_dt.strftime("%Y-%m-%d") if new_date.lower() == "none" else parse_date(new_date)

        # Construct the new meeting datetime string.
        new_meeting_datetime_str = f"{new_date_val} {new_time_val}:00"
        new_dt = datetime.strptime(new_meeting_datetime_str, "%Y-%m-%d %H:%M:%S")

        # Update the meeting record in the database.
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE meetings SET date_time = ?, updated_at = strftime('%s','now') WHERE id = ?", (new_meeting_datetime_str, mid))
            await db.commit()

        # Notify participants in the meeting's text channel.
        text_channel = discord.utils.get(guild.text_channels, name=f"{name.lower().replace(' ', '-')}-text")
        meeting_role = guild.get_role(role_id)
        
        if text_channel and meeting_role:
            try:
                notification = f"{meeting_role.mention} **Reschedule Notice:** The meeting '{name}' has been rescheduled to <t:{int(new_dt.timestamp())}:F>."
                await text_channel.send(notification)
            except Exception as e:
                print(f"Error sending reschedule notification for meeting {name}: {e}")

        # Create a new embed using the same format as the create_meeting embed.
        discord_timestamp = f"<t:{int(new_dt.timestamp())}:F>"
        
        new_embed = discord.Embed(title=f"Meeting {name} Rescheduled!", description=f"\nMeeting ID: {mid}\n{description}", color=discord.Color.blue())
        new_embed.add_field(name="Date & Time", value=discord_timestamp, inline=True)
        new_embed.add_field(name="Text Channel", value=text_channel.mention, inline=False)
        
        voice_channel = guild.get_channel(voice_channel_id)
        new_embed.add_field(name="Voice Channel", value=voice_channel.mention, inline=False)

        # Create a view with the same MeetingButtons.
        view = MeetingButtons(meeting_role)

        # Post a new message in the forum thread.
        try:
            # Fetch the forum thread (from the stored thread_id)
            thread_channel = guild.get_channel(thread_id)
            if thread_channel is None:
                thread_channel = await self.bot.fetch_channel(thread_id)
            if thread_channel and isinstance(thread_channel, discord.Thread):
                await thread_channel.send(embed=new_embed, view=view)
            else:
                print("Forum thread not found or not a thread for posting new embed.")
        except Exception as e:
            print(f"Error posting new embed in forum thread for meeting {name}: {e}")

        # Send a confirmation message to the user.
        return await interaction.response.send_message(
            f"Meeting '{name}' has been rescheduled to {discord_timestamp}. A new update has been posted in the forum.",
            ephemeral=True,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(RescheduleMeetingCog(bot))
