import discord, aiosqlite
from discord.ext import commands

AUTO_DRAG_VC_ID = 1346536904560082944

class AutoDrag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Check if the user joined the auto-dragging VC
        if after.channel and after.channel.id == AUTO_DRAG_VC_ID:
            meeting_role = None
            
            # Identify which meeting role the user has
            for role in member.roles:
                if role.name.startswith("Meeting: "):  # Standardized role name format
                    meeting_role = role
                    break

            if meeting_role is None:
                return  # No meeting role found, do nothing

            # Fetch the corresponding meeting voice channel from the database
            async with aiosqlite.connect("database.db") as db:
                async with db.execute(
                    "SELECT voice_channel_id FROM meetings WHERE name = ?", (meeting_role.name[9:],)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row is None:
                        return  # Meeting not found in DB

                    meeting_vc_id = row[0]

            # Fetch the meeting voice channel and move the user
            meeting_vc = member.guild.get_channel(meeting_vc_id)
            if meeting_vc and isinstance(meeting_vc, discord.VoiceChannel):
                try:
                    await member.move_to(meeting_vc)
                except discord.Forbidden as e:
                    print(f"Bot lacks permission to move {member} to {meeting_vc.name}. Error: {e.status} - {e.text}")
                except Exception as e:
                    print(f"Error moving {member}: {e}")

async def setup(bot):
    await bot.add_cog(AutoDrag(bot))
