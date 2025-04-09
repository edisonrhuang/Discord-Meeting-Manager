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
    Cog to list all meetings that a user is opted into.

    This command queries the database to fetch all meetings in which the user
    participates.
    Each meeting shows its ID, name, date/time, description, and platform (e.g. 'Discord').
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="list_meetings",
        description="Lists all meetings you are opted into along with their platform.",
    )
    async def list_meetings(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # SQL query to join participants and meetings to get meeting details for the user.
        query = """
            SELECT m.id, m.name, m.date_time, m.description, m.platform
            FROM participants p
            JOIN meetings m ON p.meeting_id = m.id
            WHERE p.user_id = ?
        """

        try:
            async with aiosqlite.connect(DATABASE_PATH, timeout=10) as db:
                async with db.execute(query, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
        except Exception as e:
            return await interaction.response.send_message(f"Error accessing the database: {e}", ephemeral=True)

        if not rows:
            return await interaction.response.send_message("You are not opted into any meetings.", ephemeral=True)

        # Build an embed that lists each meeting.
        embed = discord.Embed(
            title="Your Meetings",
            description="Below are the meetings you are opted into. The platform indicates where the meeting is managed.",
            color=discord.Color.blue(),
        )

        for row in rows:
            meeting_id, name, date_time_str, description, platform = row
            # Parse the meeting's date_time and convert to a Discord timestamp.
            try:
                dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
                discord_timestamp = f"<t:{int(dt.timestamp())}:F>"
            except Exception:
                # If parsing fails, show the raw string.
                discord_timestamp = date_time_str

            # If no platform is recorded, default to "Discord"
            platform_label = platform if platform else "Discord"

            embed.add_field(
                name=f"{name} (ID: {meeting_id})",
                value=(f"**Date & Time:** {discord_timestamp}\n" f"**Description:** {description if description else 'N/A'}\n" f"**Platform:** {platform_label}"),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListMeetingsCog(bot))
