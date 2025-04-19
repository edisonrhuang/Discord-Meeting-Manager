import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands
from datetime import datetime

GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))
DATABASE_PATH = "database.db"

class SearchMeetingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="search_meetings",
        description = "Search for meetings based on various criteria"
    )

    @app_commands.describe(
        keyword = "What to search for in meeting titles/descriptions"
    )

    @app_commands.guilds(GUILD_ID)
    # Simple meeting search by
    async def search_meetings(self, interaction: discord.Interaction, keyword: str):
        """Simple meeting search by keyword"""

        #Connects to database.db
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.cursor()

            await cursor.execute(
                """SELECT * FROM meetings
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY date_time ASC""",
                (f"%{keyword}%", f"%{keyword}%")
            )

            # Fetch all matching meetings
            meetings = await cursor.fetchall()

            #If no meetings found, send message and return
            if not meetings:
                return await interaction.response.send_message(
                    f"No meetings found containing ' {keyword}'",
                    ephemeral=True
                )
            
            # Response message with meeting details
            response = [f"** Meetings containing '{keyword}':**"]
            for meeting in meetings:
                response.append(
                    f"\n**{meeting[1]}** (ID: {meeting[0]})"
                    f"\n- When: {meeting[4]}"
                    f"\n- Host: <@{meeting[3]}>"
                    f"\n----------------------------------"
                )

            await interaction.response.send_message(
                    "\n".join(response),
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(SearchMeetingCog(bot))

