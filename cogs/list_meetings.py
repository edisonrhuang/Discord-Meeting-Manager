import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# Load GUILD_ID from .env file
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))
DATABASE_PATH = "database.db"


class ListMeetingsCog(commands.Cog):
    """
    Cog to list all meetings that a user is opted into on Discord.

    This command fetches all scheduled meetings (status = 'scheduled') from the database
    in which the user is registered, sorts them by their scheduled date/time, and displays
    them in a single embed.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="list_meetings",
        description="Lists all meetings you are opted into on Discord.",
    )
    @app_commands.guilds(GUILD_ID)
    async def list_meetings(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_name = interaction.guild.name  # Name of the current server.
        discord_emoji = discord.utils.get(interaction.guild.emojis, name="discord_logo")

        if discord_emoji:
            embed_title = f"{discord_emoji} Meetings in {guild_name}"
        else:
            embed_title = f"Meetings in {guild_name}"

        # SQL query to join participants and meetings to get meeting details.
        query = """
            SELECT m.id, m.name, m.date_time, m.description
            FROM participants p
            JOIN meetings m ON p.meeting_id = m.id
            WHERE p.user_id = ? AND m.status = 'scheduled'
        """

        try:
            async with aiosqlite.connect(DATABASE_PATH, timeout=10) as db:
                async with db.execute(query, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
        except Exception as e:
            return await interaction.response.send_message(f"Error accessing the database: {e}", ephemeral=True)

        # Check if the user is opted into any meetings.
        if not rows:
            return await interaction.response.send_message("You are not opted into any meetings.", ephemeral=True)

        # Process the returned rows.
        meetings = []
        for row in rows:
            meeting_id, name, date_time_str, description = row

            # Convert the date_time string to a datetime object.
            try:
                dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = None  # Fallback if parsing fails.

            meetings.append(
                {
                    "id": meeting_id,
                    "name": name,
                    "date_time_str": date_time_str,
                    "dt": dt,
                    "description": description or "N/A",
                }
            )

        # Sort meetings based on datetime (unknown datetime values will appear last).
        meetings.sort(key=lambda m: m["dt"] if m["dt"] is not None else datetime.max)

        meeting_list_str = ""
        for meeting in meetings:
            if meeting["dt"]:
                # Use Discord's timestamp format for nicer display.
                timestamp = f"<t:{int(meeting['dt'].timestamp())}:F>"
            else:
                timestamp = meeting["date_time_str"]
            meeting_list_str += f"**{meeting['name']}** (ID: {meeting['id']}) - {timestamp}\n" f"Description: {meeting['description']}\n\n"

        embed = discord.Embed(
            title=embed_title,
            description=meeting_list_str,
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListMeetingsCog(bot))
