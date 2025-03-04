import discord
import aiosqlite
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
            
            # Identify which meeting role the user has (async loop to await DB check)
            for role in member.roles:
                if await self.is_meeting_role(role.id):
                    meeting_role = role
                    break  # Stop searching once we find a valid meeting role

            if meeting_role is None:
                return  # No valid meeting role found, do nothing

            # Fetch the corresponding meeting voice channel from the database
            async with aiosqlite.connect("database.db") as db:
                async with db.execute(
                    "SELECT voice_channel_id FROM meetings WHERE role_id = ?", (meeting_role.id,)
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
                except discord.Forbidden:
                    print(f"Bot lacks permission to move {member} to {meeting_vc.name}.")
                except Exception as e:
                    print(f"Error moving {member}: {e}")

    async def is_meeting_role(self, role_id: int) -> bool:
        """Check if the role ID exists in the meetings table."""
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT 1 FROM meetings WHERE role_id = ?", (role_id,)) as cursor:
                return await cursor.fetchone() is not None

async def setup(bot):
    await bot.add_cog(AutoDrag(bot))
