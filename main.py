import discord, os, dotenv, aiosqlite
from discord.ext import commands

dotenv.load_dotenv()

# SERVER ID
GUILD_ID = discord.Object(id=1337086900409864224)

class Client(commands.Bot):
    async def setup_hook(self):
        # Dynamically load all Cog files from the cogs folder.
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                extension = f"cogs.{filename[:-3]}" # -3 to remove .py
                try:
                    await self.load_extension(extension)
                    print(f"Loaded extension: {extension}")
                except Exception as e:
                    print(f"Failed to load extension {extension}: {e}")
    
    async def on_ready(self):
        self.db = await aiosqlite.connect("database.db")
        cursor = await self.db.cursor()

        await cursor``.execute("")
        await self.db.commit()

        # Sync the command tree for the specific guild so that the slash commands are registered immediately.
        try:
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} command(s) for guild {GUILD_ID.id}")
        except Exception as e:
            print(f"Error syncing commands: (e)")
        print(f'Logged on as {self.user}')

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="/", intents=intents)

# Run bot with given token
client.run(f"{os.getenv('DEV_TOKEN')}")