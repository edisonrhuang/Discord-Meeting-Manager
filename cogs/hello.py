# commands/hello.py

import discord
from discord import app_commands
from discord.ext import commands

# SERVER ID
GUILD_ID = discord.Object(id=1337086900409864224)

class Hello(commands.Cog):
    """A Cog for the /hello command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello!")
    @app_commands.guilds(GUILD_ID) # Register command to the server
    async def hello(self, interaction: discord.Interaction):
        # Respond to the slash command with a mention.
        await interaction.response.send_message(f"Hello {interaction.user.mention}!")

async def setup(bot):
    await bot.add_cog(Hello(bot))
