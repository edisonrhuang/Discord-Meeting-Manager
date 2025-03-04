# commands/hello.py

import discord, os
from discord import app_commands
from discord.ext import commands

# SERVER ID
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))


# Create a Cog for the hello command
class Hello(commands.Cog):
    # Initialize the Cog with the bot instance
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Define the hello command as a slash command
    @app_commands.command(name="hello", description="Say hello!")
    @app_commands.guilds(GUILD_ID)  # Register command to the server

    # Define the command function
    async def hello(self, interaction: discord.Interaction):
        # Respond to the slash command with a mention.
        await interaction.response.send_message(f"Hello {interaction.user.mention}!")


# Setup function to add the Cog to the bot
async def setup(bot):
    await bot.add_cog(Hello(bot))
