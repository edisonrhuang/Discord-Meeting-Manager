import discord, aiosqlite, asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta

DATABASE_PATH = "database.db"


class UpcomingMeetingReminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminded_meetings = set()  # Store IDs of meetings that got a reminder
        self.check_meetings.start()  # Start the loop when the cog is loaded

    def cog_unload(self):
        self.check_meetings.cancel()  # Cancel the loop when the cog is unloaded

    @tasks.loop(seconds=15)
    async def check_meetings(self):
        now = datetime.now()
        reminder_time = now + timedelta(minutes=15)

        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                """
                SELECT id, name, date_time, role_id, thread_id
                FROM meetings
                WHERE status = 'scheduled' AND date_time BETWEEN ? AND ?
                """,
                (now.strftime("%Y-%m-%d %H:%M:%S"), reminder_time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            meetings = await cursor.fetchall()

        for meeting in meetings:
            meeting_id, name, date_time_str, role_id, thread_id = meeting
            meeting_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")

            # Skip if reminder already sent
            if meeting_id in self.reminded_meetings:
                continue

            # calculate the actual remaining time in minutes
            time_remaining = meeting_time - now
            minutes_remaining = int(time_remaining.total_seconds() // 60)
            if minutes_remaining <= 0:
                continue  # skip if the meeting has already started

            guild = self.bot.get_guild(int(self.bot.guilds[0].id))
            if guild is None:
                print(f"Guild not found for meeting {name}.")
                continue

            role = guild.get_role(role_id)
            thread = guild.get_thread(thread_id)

            if role and thread:
                try:
                    await thread.send(f"{role.mention} Reminder: The meeting **{name}** is starting in "
                    f"{minutes_remaining} minute{'s' if minutes_remaining != 1 else ''} at <t:{int(meeting_time.timestamp())}:F>.")
                    self.reminded_meetings.add(meeting_id)
                except Exception as e:
                    print(f"Failed to send reminder for meeting {name}: {e}")

    @check_meetings.before_loop
    async def before_check_meetings(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready


async def setup(bot: commands.Bot):
    await bot.add_cog(UpcomingMeetingReminder(bot))
