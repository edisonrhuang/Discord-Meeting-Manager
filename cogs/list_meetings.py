import discord
import os
import aiosqlite
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# Load GUILD_ID from .env file
GUILD_ID = discord.Object(id=(os.getenv("GUILD_ID")))
DATABASE_PATH = "database.db"


class SortMeetingsView(discord.ui.View):
    """
    A View with buttons to re-sort the meeting list.

    This view stores the meetings and the embed title.
    Each button's callback sorts the meeting list based on a specific criterion
    (date/time, title, or ID) and toggles between ascending and descending order.
    It then updates the original message's embed.
    """

    def __init__(self, meetings, embed_title):
        super().__init__(timeout=None)
        self.meetings = meetings
        self.embed_title = embed_title

        # Store sorting order per criterion: True means ascending; False means descending.
        self.sort_orders = {"date": False, "title": True, "id": True}

    def build_embed(self) -> discord.Embed:

        description = "These are the meetings you are opted into for this server.\nThe buttons below will change the order in which the meetings are sorted.\n\n"

        meeting_list_str = ""
        for meeting in self.meetings:
            if meeting["dt"]:
                # Format the datetime as a Discord timestamp.
                timestamp = f"<t:{int(meeting['dt'].timestamp())}:F>"
            else:
                timestamp = meeting["date_time_str"]
            meeting_list_str += f"**{meeting['name']}** (ID: {meeting['id']}) - {timestamp}\n" f"Description: {meeting['description']}\n\n"

        full_description = description + meeting_list_str
        embed = discord.Embed(
            title=self.embed_title,
            description=full_description,
            color=discord.Color.blue(),
        )
        return embed

    @discord.ui.button(label="Sort by Date/Time", style=discord.ButtonStyle.primary)
    async def sort_by_date(self, interaction: discord.Interaction, button: discord.ui.Button):
        ascending = self.sort_orders["date"]

        # If ascending is True, sort ascending; if False, sort descending.
        self.meetings.sort(key=lambda m: m["dt"] if m["dt"] is not None else datetime.max, reverse=not ascending)

        # Toggle sort order for next click.
        self.sort_orders["date"] = not ascending
        new_embed = self.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Sort by Title", style=discord.ButtonStyle.primary)
    async def sort_by_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        ascending = self.sort_orders["title"]
        self.meetings.sort(key=lambda m: m["name"].lower(), reverse=not ascending)
        self.sort_orders["title"] = not ascending
        new_embed = self.build_embed()

        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Sort by ID", style=discord.ButtonStyle.primary)
    async def sort_by_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        ascending = self.sort_orders["id"]
        self.meetings.sort(key=lambda m: m["id"], reverse=not ascending)
        self.sort_orders["id"] = not ascending
        new_embed = self.build_embed()

        await interaction.response.edit_message(embed=new_embed, view=self)


class ListMeetingsCog(commands.Cog):
    """
    Cog to list all scheduled meetings that a user is opted into on Discord.

    This command fetches the user's meetings, sorts them (default by date/time),
    and sends an embed that can be re-sorted interactively using buttons.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="list_meetings",
        description="Lists all meetings you are opted into on Discord.",
    )
    @app_commands.guilds(GUILD_ID)
    async def list_meetings(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_name = interaction.guild.name  # Name of the current server.
        discord_emoji = discord.utils.get(interaction.guild.emojis, name="discord_logo")

        if discord_emoji:
            embed_title = f"{discord_emoji} Meetings in {guild_name}"
        else:
            embed_title = f"Meetings in {guild_name}"

        # SQL query to join participants and meetings to get meeting details.
        query = """
            SELECT m.id, m.name, m.date_time, m.description
            FROM participants p
            JOIN meetings m ON p.meeting_id = m.id
            WHERE p.user_id = ? AND m.status = 'scheduled'
        """

        try:
            async with aiosqlite.connect(DATABASE_PATH, timeout=10) as db:
                async with db.execute(query, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
        except Exception as e:
            return await interaction.response.send_message(f"Error accessing the database: {e}", ephemeral=True)

        # Check if the user is opted into any meetings.
        if not rows:
            return await interaction.response.send_message("You are not opted into any meetings.", ephemeral=True)

        # Process the returned rows.
        meetings = []
        for row in rows:
            meeting_id, name, date_time_str, description = row

            # Convert the date_time string to a datetime object.
            try:
                dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = None  # Fallback if parsing fails.

            meetings.append(
                {
                    "id": meeting_id,
                    "name": name,
                    "date_time_str": date_time_str,
                    "dt": dt,
                    "description": description or "N/A",
                }
            )

        # Default sort: by date/time.
        meetings.sort(key=lambda m: m["dt"] if m["dt"] is not None else datetime.max)

        # Create a view with sorting buttons.
        view = SortMeetingsView(meetings, embed_title)
        embed = view.build_embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListMeetingsCog(bot))
