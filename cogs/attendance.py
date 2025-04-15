import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands

DATABASE_PATH = "database.db"
GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))

class AttendanceCog(commands.Cog):
    """Displays attendance information for a meeting by listing opted in users and who has joined the voice channel at any time."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.ensure_attendance_table())

    async def ensure_attendance_table(self):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_log (
                    meeting_id INTEGER,
                    user_id INTEGER,
                    joined_at TEXT DEFAULT (strftime('%s','now')),
                    UNIQUE(meeting_id, user_id)
                )
                """
            )
            await db.commit()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Check if the user has just joined a voice channel
        if before.channel is None and after.channel is not None:
            voice_channel = after.channel
            # Check if this voice channel is linked to a meeting
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT id FROM meetings WHERE voice_channel_id = ?", (voice_channel.id,),) as cursor:
                    meeting_row = await cursor.fetchone()
            if meeting_row:
                meeting_id = meeting_row[0]
                # Record the attendance event, ignoring duplicates
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    await db.execute("INSERT OR IGNORE INTO attendance_log (meeting_id, user_id) VALUES (?, ?)",(meeting_id, member.id),)
                    await db.commit()

    @app_commands.command(
        name="attendance",
        description="Shows the attendance for a meeting by listing opted-in users and those who joined the voice channel."
    )

    @app_commands.describe(meeting_id="The id of the meeting to show attendance for")
    @app_commands.guilds(GUILD_ID)
    async def attendance(self, interaction: discord.Interaction, meeting_id: int):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        
        # Get meeting details from the database to get meeting name and voice channel id
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT name, voice_channel_id FROM meetings WHERE id = ?", (meeting_id,)) as cursor:
                meeting = await cursor.fetchone()
        
        if meeting is None:
            return await interaction.response.send_message(f"No meeting found with id {meeting_id}.", ephemeral=True)
        
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
        
        # Get users who have joined the voice channel
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT user_id FROM attendance_log WHERE meeting_id = ?", (meeting_id,),) as cursor:
                attendance_rows = await cursor.fetchall()
        attendance_ids = [row[0] for row in attendance_rows]
        attendance_list = "\n".join(f"<@{user_id}>" for user_id in attendance_ids) if attendance_ids else "No users have joined the voice channel."
        

        # Output lists of users
        embed = discord.Embed(title=f"Attendance for Meeting: {meeting_name} (ID: {meeting_id})", color=discord.Color.blue())
        embed.add_field(name="Opted-In Participants", value=opted_in_list, inline=False)
        embed.add_field(name="Voice Channel Join History", value=attendance_list, inline=False)
        embed.set_footer(text="Attendance is based on who has joined the voice channel at any time.")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AttendanceCog(bot))
