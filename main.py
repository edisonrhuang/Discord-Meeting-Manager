import discord, os, dotenv, aiosqlite
from discord.ext import commands

dotenv.load_dotenv()

# SERVER ID
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))


class Client(commands.Bot):
    async def setup_hook(self):
        # Dynamically load all Cog files from the cogs folder.
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                extension = f"cogs.{filename[:-3]}"  # -3 to remove .py
                try:
                    await self.load_extension(extension)
                    print(f"Loaded extension: {extension}")
                except Exception as e:
                    print(f"Failed to load extension {extension}: {e}")

    async def create_database(self):
        # Creates the SQLite database and intializes tables.
        self.db = await aiosqlite.connect("database.db")
        cursor = await self.db.cursor()

        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                host_id INTEGER NOT NULL, --Discord User ID
                date_time INTEGER, --Unix timestamp (seconds)
                duration INTEGER, --In minutes
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now')),
                status TEXT CHECK(status IN ('scheduled', 'cancelled', 'completed')) DEFAULT 'scheduled',
                voice_channel_id INTEGER,
                thread_id INTEGER,
                recurring_interval TEXT CHECK(recurring_interval IN ('none', 'daily', 'weekly', 'monthly')) DEFAULT 'none',
                recurring_end_date INTEGER --Unix timestamp (seconds)
            );
        """)

        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                meeting_id INTEGER,
                user_id, INTEGER,
                FOREIGN KEY (meeting_id) references meetings(id) ON DELETE CASCADE
            );
        """)

        await self.db.commit()
        print("Database initialized successfully.")

    async def on_ready(self):
        await self.create_database()

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