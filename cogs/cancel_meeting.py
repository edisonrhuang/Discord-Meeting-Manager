import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands

GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))
DATABASE_PATH = "database.db"

class CancelMeetingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cancel_meeting",
        description="Cancels a meeting: updates status, cleans up channels/role,and message in the forum post."
    )
    @app_commands.describe(meeting_title="The title of the meeting to cancel")
    @app_commands.guilds(GUILD_ID)
    async def cancel_meeting(self, interaction: discord.Interaction, meeting_title: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        # retrieve meeting details using the meeting title.
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute(
                "SELECT name, voice_channel_id, thread_id, role_id, status FROM meetings WHERE name = ?",
                (meeting_title,)
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return await interaction.response.send_message(f"Meeting with title '{meeting_title}' not found.", ephemeral=True)

        name, voice_channel_id, thread_id, role_id, status = row
        if status == "cancelled":
            return await interaction.response.send_message(f"The meeting '{name}' is already cancelled.", ephemeral=True)

        # Update the meeting status to 'cancelled' in the database.
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE meetings SET status = 'cancelled', updated_at = strftime('%s','now') WHERE name = ?",
                (meeting_title,)
            )
            await db.commit()

        # delete text
        text_channel_name = f"{meeting_title.lower().replace(' ', '-')}-text"
        text_channel = discord.utils.get(guild.text_channels, name=text_channel_name)
        if text_channel:
            try:
                await text_channel.delete(reason="Meeting cancelled")
            except Exception as e:
                print(f"Error deleting text channel '{text_channel.name}': {e}")

        # delete voice channel
        voice_channel = guild.get_channel(voice_channel_id)
        if voice_channel:
            try:
                await voice_channel.delete(reason="Meeting cancelled")
            except Exception as e:
                print(f"Error deleting voice channel: {e}")

        # delete role
        meeting_role = guild.get_role(role_id)
        if meeting_role:
            try:
                await meeting_role.delete(reason="Meeting cancelled")
            except Exception as e:
                print(f"Error deleting meeting role: {e}")

        # Get the forum post channel
        thread_channel = guild.get_channel(thread_id)
        if thread_channel is None:
            try:
                thread_channel = await self.bot.fetch_channel(thread_id)
            except Exception as e:
                print(f"Error fetching thread channel: {e}")

        if thread_channel and isinstance(thread_channel, discord.Thread):
            try:
                if thread_channel.archived:
                    await thread_channel.edit(archived=False)
                cancellation_message = f"**Cancellation Notice:** This meeting has been cancelled."
                await thread_channel.send(cancellation_message)
            except Exception as e:
                print(f"Error sending cancellation message in thread: {e}")
        else:
            print("Thread channel not found or not a thread.")

        await interaction.response.send_message(
            f"Meeting '{meeting_title}' has been cancelled and a notice has been posted in the forum.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CancelMeetingCog(bot))
