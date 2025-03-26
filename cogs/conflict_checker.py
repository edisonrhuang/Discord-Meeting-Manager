import discord, os, aiosqlite
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from collections import defaultdict

GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))
DEFAULT_DURATION_MINUTES = 60  # default meeting duration since none is provided **NEED TO CHANGE WHEN DURATION IS ADDED TO MEETING CREATION**

class ConflictCheckerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.notified_conflicts = {}  # {user_id: (timestamp, conflict_set)}
        self.check_conflicts_loop.start()
    
    def cog_unload(self):
        self.check_conflicts_loop.cancel()
    
    @tasks.loop(minutes=1)
    async def check_conflicts_loop(self):
        """
        checks for scheduling conflicts for all users in the background.
        if conflicts are found or change, the user is notified via DM.
        """
        async with aiosqlite.connect("database.db") as db:
            cursor = await db.execute(
                "SELECT p.user_id, m.id, m.name, m.date_time, m.duration FROM meetings m "
                "INNER JOIN participants p ON m.id = p.meeting_id WHERE m.status = 'scheduled'"
            )
            rows = await cursor.fetchall()
        
        # group meetings by user_id
        user_meetings = defaultdict(list)
        for row in rows:
            user_id, meeting_id, name, date_time_str, duration = row
            try:
                start_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if not duration or duration == 0:
                duration = DEFAULT_DURATION_MINUTES
            end_time = start_time + timedelta(minutes=duration)
            user_meetings[user_id].append({"meeting_id": meeting_id, "name": name, "start_time": start_time, "end_time": end_time})
        
        # check for overlapping meetings for each user
        for user_id, meetings in user_meetings.items():
            if len(meetings) < 2:
                # clear any stored conflict if no conflict is possible now.
                if user_id in self.notified_conflicts:
                    del self.notified_conflicts[user_id]
                continue
            
            # find meetings that conflict
            meetings.sort(key=lambda m: m["start_time"])
            conflict_pairs = []
            for i in range(len(meetings)):
                for j in range(i + 1, len(meetings)):
                    a = meetings[i]
                    b = meetings[j]
                    if a["end_time"] > b["start_time"]:
                        pair = tuple(sorted((a["meeting_id"], b["meeting_id"])))
                        conflict_pairs.append(pair)
            
            current_conflicts = set(conflict_pairs)
            now_ts = datetime.now().timestamp()
            notify = False
            
            if user_id not in self.notified_conflicts:
                # never notified before, send notification.
                notify = True
            else:
                last_ts, last_conflicts = self.notified_conflicts[user_id]
                # conflict has changed, send a notification regardless of cooldown.
                if current_conflicts != last_conflicts:
                    notify = True
                # else notify if more than 15 minutes have passed.
                elif now_ts - last_ts > 15 * 60:
                    notify = True
            
            # notify user about conflict
            if notify and current_conflicts:
                user = self.bot.get_user(user_id)
                if not user:
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except Exception as e:
                        print(f"Could not fetch user {user_id}: {e}")
                        continue
                if user:
                    message = "⚠️ **Scheduling Conflict Detected!** ⚠️\n"
                    message += "You have overlapping meetings:\n"
                    for conflict in current_conflicts:
                        # get meeting details for each meeting
                        m1 = next((m for m in meetings if m["meeting_id"] == conflict[0]), None)
                        m2 = next((m for m in meetings if m["meeting_id"] == conflict[1]), None)
                        if m1 and m2:
                            message += (f"• Meeting **{m1['name']}** starts at {m1['start_time'].strftime('%m-%d-%Y %I:%M %p')} and ends at {m1['end_time'].strftime('%I:%M %p')}\n"
                                f"• Meeting **{m2['name']}** starts at {m2['start_time'].strftime('%m-%d-%Y %I:%M %p')} and ends at {m2['end_time'].strftime('%I:%M %p')}\n")
                    try:
                        await user.send(message)
                        self.notified_conflicts[user_id] = (now_ts, current_conflicts)
                    except Exception as e:
                        print(f"Failed to send conflict notification to user {user_id}: {e}")
    
    @check_conflicts_loop.before_loop
    async def before_check_conflicts(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ConflictCheckerCog(bot))
