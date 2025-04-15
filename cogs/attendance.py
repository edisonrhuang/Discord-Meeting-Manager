import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands

DATABASE_PATH = "database.db"
GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))

class AttendanceCog(commands.Cog):
    """Displays attendance information for a meeting by listing opted in users and who is currently in the voice channel."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="attendance",
        description="Shows the attendance for a meeting by listing opted-in users and those in the voice channel."
    )

    @app_commands.describe(meeting_id="The id of the meeting to show attendance for")
    @app_commands.guilds(GUILD_ID)
    async def attendance(self, interaction: discord.Interaction, meeting_id: int):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
        
        # Get meeting details from the database to get meeting name and voice channel id
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT name, voice_channel_id FROM meetings WHERE id = ?", (meeting_id,)) as cursor:
                meeting = await cursor.fetchone()
        
        if meeting is None:
            return await interaction.response.send_message(
                f"No meeting found with id {meeting_id}.", ephemeral=True
            )
        
        meeting_name, voice_channel_id = meeting
        
        # Get opted-in user IDs from participants table
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM participants WHERE meeting_id = ?", (meeting_id,)) as cursor:
                rows = await cursor.fetchall()
        opted_in_ids = [row[0] for row in rows]
        
        if opted_in_ids:
            opted_in_list = "\n".join(f"<@{user_id}>" for user_id in opted_in_ids)
        else:
            opted_in_list = "No participants have opted in."
        
        # Get users currently in the voice channel.
        voice_channel_participants = []
        if voice_channel_id:
            channel = guild.get_channel(voice_channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                voice_channel_participants = channel.members
        
        if voice_channel_participants:
            voice_participants_list = "\n".join(member.mention for member in voice_channel_participants)
        else:
            voice_participants_list = "No users are currently in the voice channel."

        # Output list of users
        embed = discord.Embed(
            title=f"Attendance for Meeting: {meeting_name} (ID: {meeting_id})",
            color=discord.Color.blue()
        )
        embed.add_field(name="Opted-In Participants", value=opted_in_list, inline=False)
        embed.add_field(name="Voice Channel Participants", value=voice_participants_list, inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AttendanceCog(bot))
