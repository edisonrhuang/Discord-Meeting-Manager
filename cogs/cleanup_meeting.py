import discord, os, aiosqlite, asyncio
from discord import app_commands
from discord.ext import commands

GUILD_ID = discord.Object(id=(int(os.getenv("GUILD_ID"))))  # Ensure GUILD_ID is an integer
DATABASE_PATH = "database.db"

class CleanupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cleanup",
        description="Cleans up a meeting by deleting its resources.",
    )
    @app_commands.describe(meeting_id="The ID of the meeting to clean up")
    @app_commands.guilds(GUILD_ID)
    async def cleanup_meeting(self, interaction: discord.Interaction, meeting_id: int):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT name, voice_channel_id, role_id, thread_id FROM meetings WHERE id = ?", (meeting_id,))
            meeting_data = await cursor.fetchone()

            if not meeting_data:
                return await interaction.response.send_message("Meeting not found.", ephemeral=True)

            name, voice_channel_id, role_id, thread_id = meeting_data
            expected_name = f"{name.lower().replace(' ', '-')}-text"

            # Delete voice channel
            if voice_channel_id:
                voice_channel = guild.get_channel(voice_channel_id)
                if voice_channel:
                    await voice_channel.delete()

            # Delete role
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    await role.delete()

            # Move text channel to "Meeting Archive"
            meetings_archive_category = discord.utils.get(guild.categories, name="Meeting Archive")
            if not meetings_archive_category:
                return await interaction.response.send_message("The 'Meeting Archive' category does not exist.", ephemeral=True)
            
            meeting_text_channel = discord.utils.get(guild.text_channels, name=expected_name)
            if meeting_text_channel:
                try:
                    # Send archive message
                    await meeting_text_channel.send("This meeting has been archived and moved to the Meeting Archive.")
                    await meeting_text_channel.edit(category=meetings_archive_category)
                except Exception as e:
                    print(f"Error moving text channel: {e}")

            # Get the forum post channel
            thread_channel = guild.get_channel(thread_id)
            if thread_channel is None:
                try:
                    thread_channel = await self.bot.fetch_channel(thread_id)
                except Exception as e:
                    print(f"Error fetching thread channel: {e}")

            # Send message to forum thread
            if thread_channel and isinstance(thread_channel, discord.Thread):
                try:
                    archive_message = "**This meeting is now archived. No further discussion is expected.**"
                    await thread_channel.send(archive_message)
        
                    # Re-archive and lock the thread after sending the message
                    await thread_channel.edit(archived=True, locked=True)

                except Exception as e:
                    print(f"Error sending archive message in thread: {e}")
            else:
                print("Thread channel not found or not a thread.")


            # Delete meeting entry from database
            await db.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            await db.commit()

        await interaction.response.send_message(f"Meeting {meeting_id} cleaned up successfully.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CleanupCog(bot))
