import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands

GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))
DATABASE_PATH = "database.db"


class ChangeStatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="change_status",
        description="Set your availability status"
    )
    @app_commands.describe(current_status="Set to 'Available' or 'Busy")
    @app_commands.choices(
        current_status=[
            app_commands.Choice(name="Available", value="Available"),
            app_commands.Choice(name="Busy", value = "Busy")
        ]

    )
    @app_commands.guilds(GUILD_ID)
    async def availability(self, interaction: discord.Interaction, current_status: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephermal=True)
        
        user_id = interaction.user.id
        
        
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    """
                    INSERT INTO participants (user_id, current_status)
                    VALUES (?,?)
                    """,
                    (user_id, current_status),
                )
                await db.commit()
            
            await interaction.response.send_message(
            f"{interaction.user.mention} is now {current_status}!",
            ephemeral=-False
            )
        except Exception as e:
            await interaction.response.send_message(f"An error occurred while updating your status: {e}", ephemeral=True)

    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(ChangeStatusCog(bot))
