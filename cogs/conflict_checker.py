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
                "SELECT DISTINCT p.user_id, m.id, m.name, m.date_time, m.duration FROM meetings m "
                "INNER JOIN participants p ON m.id = p.meeting_id WHERE m.status = 'scheduled'"
            )
            rows = await cursor.fetchall()
        
        # group meetings by user_id
        user_meetings = defaultdict(dict)
        for row in rows:
            user_id, meeting_id, name, date_time_str, duration = row
            try:
                start_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if not duration or duration == 0:
                duration = DEFAULT_DURATION_MINUTES
            end_time = start_time + timedelta(minutes=duration)
            user_meetings[user_id][meeting_id] = {"meeting_id": meeting_id, "name": name, "start_time": start_time, "end_time": end_time}
        
        # check for overlapping meetings for each user
        for user_id, meetings_dict in user_meetings.items():
            meetings = list(meetings_dict.values())
            if len(meetings) < 2:
                # clear any stored conflict if no conflict is possible now.
                self.notified_conflicts.pop(user_id, None)
                continue
            
            # find meetings that conflict
            meetings.sort(key=lambda m: m["start_time"])
            conflict_entries = []
            for i in range(len(meetings)):
                for j in range(i + 1, len(meetings)):
                    a = meetings[i]
                    b = meetings[j]
                    # Check if meeting a conflicts with meeting b
                    if a["end_time"] > b["start_time"]:
                        entry = (
                            f"• Meeting **{a['name']}** starts at {a['start_time'].strftime('%m-%d-%Y %I:%M %p')} and ends at {a['end_time'].strftime('%I:%M %p')}\n"
                            f"• Meeting **{b['name']}** starts at {b['start_time'].strftime('%m-%d-%Y %I:%M %p')} and ends at {b['end_time'].strftime('%I:%M %p')}\n"
                        )
                        conflict_entries.append(entry)
            
            if conflict_entries:
                new_conflict_message = "⚠️ **Scheduling Conflict Detected!** ⚠️\nYou have overlapping meetings:\n" + "\n".join(conflict_entries)
                now_ts = datetime.now().timestamp()

                # notify if haven't, message has changed, or its been over 15 min
                if (
                    user_id not in self.notified_conflicts or
                    self.notified_conflicts[user_id][1] != new_conflict_message or
                    now_ts - self.notified_conflicts[user_id][0] > 15 * 60
                ):
                    user = self.bot.get_user(user_id)
                    if not user:
                        try:
                            user = await self.bot.fetch_user(user_id)
                        except Exception as e:
                            print(f"Could not fetch user {user_id}: {e}")
                            continue
                    try:
                        await user.send(new_conflict_message)
                        self.notified_conflicts[user_id] = (now_ts, new_conflict_message)
                    except Exception as e:
                        print(f"Failed to send conflict notification to user {user_id}: {e}")
            else:
                # no conflicts
                self.notified_conflicts.pop(user_id, None)
    
    @check_conflicts_loop.before_loop
    async def before_check_conflicts(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ConflictCheckerCog(bot))
