import discord, os, dotenv, aiosqlite
from discord.ext import commands

dotenv.load_dotenv()

# SERVER ID
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))


async def ensure_custom_emoji(guild: discord.Guild, emoji_name: str, image_path: str) -> discord.Emoji:
    """
    Checks if an emoji with the given name exists in the guild.
    If not, reads the image from image_path and creates it.
    Returns the emoji (existing or new), or None if creation fails.
    """
    # Check if the emoji already exists
    existing = discord.utils.get(guild.emojis, name=emoji_name)
    if existing:
        return existing

    # Read the image file as bytes (ensure it's less than 256KB and in a supported format, e.g. PNG)
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
    except Exception as e:
        print(f"Error reading image file {image_path}: {e}")
        return None

    # Check if the image size is within Discord's limits (256KB)
    try:
        emoji = await guild.create_custom_emoji(name=emoji_name, image=image_bytes)
        print(f"Created emoji: {emoji}")
        return emoji
    except Exception as e:
        print(f"Error creating emoji {emoji_name} in guild {guild.name}: {e}")
        return None


class Client(commands.Bot):
    async def setup_hook(self):
        await self.create_database()

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

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                host_id INTEGER NOT NULL, --Discord User ID
                date_time TEXT, --Unix timestamp (seconds)
                duration INTEGER, --In minutes
                created_at TEXT DEFAULT (strftime('%s', 'now')),
                updated_at TEXT DEFAULT (strftime('%s', 'now')),
                status TEXT CHECK(status IN ('scheduled', 'cancelled', 'completed')) DEFAULT 'scheduled',
                platform TEXT DEFAULT 'Discord',  -- Meeting platform,
                voice_channel_id INTEGER,
                thread_id INTEGER,
                role_id INTEGER,
                recurrence INTEGER CHECK(recurrence IN (0, 1, 7, 30)) DEFAULT 0
            );
        """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                meeting_id INTEGER,
                user_id INTEGER,
                current_status TEXT CHECK(current_status IN ('Available','Busy')) DEFAULT 'Busy',
                FOREIGN KEY (meeting_id) references meetings(id) ON DELETE CASCADE
            );
        """
        )

        await self.db.commit()
        print("Database initialized successfully.")

    async def on_ready(self):
        # Sync the command tree for the specific guild so that the slash commands are registered immediately.
        try:
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} command(s) for guild {GUILD_ID.id}")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        print(f"Logged on as {self.user}")

        # After logging in, ensure the custom emoji exists.
        guild = self.get_guild(GUILD_ID.id)
        if guild:
            emoji_data = [
                ("discord_logo", "images/discord_logo.png"),
                ("google_logo", "images/google_logo.png"),
                ("outlook_logo", "images/outlook_logo.png"),
            ]
            for name, path in emoji_data:
                emoji = await ensure_custom_emoji(guild, name, path)
                if emoji:
                    print(f"Using custom emoji: {emoji}")
                else:
                    print("Custom emoji not created, ensure the image file exists and the bot has Manage/Create Expressions permission.")


intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="/", intents=intents)

# Run bot with given token
client.run(f"{os.getenv('DEV_TOKEN')}")
