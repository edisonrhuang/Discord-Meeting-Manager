import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# Load GUILD_ID from .env file
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))
DATABASE_PATH = "database.db"

# List of known platforms in the order you want them to appear.
KNOWN_PLATFORMS = ["Discord", "Google", "Outlook"]


class ListMeetingsCog(commands.Cog):
    """
    Cog to list all meetings that a user is opted into.

    This command queries the database to fetch all meetings the user participates in.
    Meetings are grouped by their platform (e.g., Discord, Google, Outlook) and sorted by
    the scheduled date/time. For each known platform, if there are no meetings, a message
    is shown stating that the user is not opted into any meetings for that platform.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="list_meetings",
        description="Lists all meetings you are opted into, grouped by platform.",
    )
    @app_commands.guilds(GUILD_ID)
    async def list_meetings(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # SQL query to join participants and meetings to get meeting details.
        query = """
            SELECT m.id, m.name, m.date_time, m.description, m.platform
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

        # Group meetings by their platform.
        groups = {}
        for row in rows:
            meeting_id, name, date_time_str, description, platform = row

            # Default platform to "Discord" if not provided.
            key = platform if platform else "Discord"

            # Attempt to parse the meeting date/time.
            try:
                dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = None  # Fallback to None if parsing fails.
            groups.setdefault(key, []).append({"id": meeting_id, "name": name, "date_time_str": date_time_str, "dt": dt, "description": description or "N/A"})

        # Create an embed that will hold the grouped meeting details.
        embed = discord.Embed(
            title="Your Meetings",
            description="Meetings grouped by platform (sorted by upcoming time):",
            color=discord.Color.blue(),
        )

        # Iterate over the known platforms in the desired order.
        for platform in KNOWN_PLATFORMS:
            # Get meetings for this platform if any.
            meetings = groups.get(platform, [])
            if meetings:
                # Sort meetings by datetime.
                sorted_meetings = sorted(meetings, key=lambda m: m["dt"] if m["dt"] is not None else datetime.max)
                meeting_list_str = ""
                for meeting in sorted_meetings:
                    # Convert the datetime to a Discord timestamp if available.
                    if meeting["dt"]:
                        timestamp = f"<t:{int(meeting['dt'].timestamp())}:F>"
                    else:
                        timestamp = meeting["date_time_str"]
                    meeting_list_str += f"**{meeting['name']}** (ID: {meeting['id']}) - {timestamp}\n" f"Description: {meeting['description']}\n\n"
            else:
                # No meetings in this platform group.
                meeting_list_str = f"You are not opted into any meetings on {platform}."

            # Look up a custom emoji in the guild with a name matching the platform (in lowercase).
            emoji = discord.utils.find(lambda e: platform.lower() in e.name, interaction.guild.emojis)
            if emoji:
                field_name = f"{emoji} | {platform} Meetings"
            else:
                field_name = f"{platform} Meetings"

            embed.add_field(name=field_name, value=meeting_list_str, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListMeetingsCog(bot))
