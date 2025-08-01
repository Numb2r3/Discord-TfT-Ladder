import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
import data_manager
import asyncio

from utils.checks import is_in_allowed_channels
import constants

# --- Logging Setup ---
USER_PY_LOGGING_PREFIX = "TFT_COG_INFO_"
try:
    import logging_setup 
    logger = logging_setup.setup_project_logger(env_prefix=USER_PY_LOGGING_PREFIX)
except ImportError:
    print(f"Error: Cannot find the 'logging_setup.py' module (for {USER_PY_LOGGING_PREFIX}).", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}Fallback')
except Exception as e:
    print(f"Error during logging setup for {USER_PY_LOGGING_PREFIX}: {e}. Using fallback.", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}SetupErrorFallback')


class LeaderboardView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, leaderboard_data: list):
        # Der Timeout für die Buttons wird auf 3 Minuten (180s) gesetzt.
        super().__init__(timeout=180)
        self.interaction = interaction
        self.leaderboard_data = leaderboard_data
        self.current_page = 0
        self.items_per_page = 10
        self.message = None

    async def _schedule_deletion(self, delay: int):
        """Wartet für die angegebene Zeit und löscht dann die Nachricht."""
        await asyncio.sleep(delay)
        try:
            if self.message:
                await self.message.delete()
                logger.info(f"Leaderboard message {self.message.id} deleted after {delay}s.")
        except discord.NotFound:
            # Die Nachricht wurde bereits manuell gelöscht, das ist in Ordnung.
            logger.info(f"Tried to delete leaderboard message, but it was already gone.")
            pass

    async def start(self):
        """Sendet die initiale Nachricht und plant deren Löschung."""
        initial_embed = await self.format_page()
        self.prev_button.disabled = True
        self.next_button.disabled = (self.current_page + 1) * self.items_per_page >= len(self.leaderboard_data)
        
        # Sende die Nachricht und speichere das Nachrichtenobjekt.
        self.message = await self.interaction.followup.send(embed=initial_embed, view=self)

        # Plane die Löschung der Nachricht in 15 Minuten (900s).
        asyncio.create_task(self._schedule_deletion(delay=3600))

    async def format_page(self) -> discord.Embed:
        """Erstellt das Embed für die aktuelle Seite."""
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        page_data = self.leaderboard_data[start_index:end_index]

        description = ""
        for i, (account, history) in enumerate(page_data, start=start_index + 1):
            tier_str = f"{history.tier.capitalize()} {history.division}"
            description += f"`{i: >2}.` **{account.game_name}#{account.tag_line}** - {tier_str} ({history.league_points} LP)\n"
        
        embed = discord.Embed(
            title=f"Leaderboard für {self.interaction.guild.name}",
            description=description,
            color=discord.Color.gold()
        )
        total_pages = -(-len(self.leaderboard_data) // self.items_per_page)
        embed.set_footer(text=f"Seite {self.current_page + 1} / {total_pages}")
        return embed

    async def update_message(self):
        """Aktualisiert die Nachricht mit der neuen Seite."""
        embed = await self.format_page()
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = (self.current_page + 1) * self.items_per_page >= len(self.leaderboard_data)
        await self.interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message()

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message()

    async def on_timeout(self) -> None:
        """Wird aufgerufen, wenn die View nach 3 Minuten abläuft."""
        if self.message:
            # Bearbeite die Nachricht, um die Buttons zu entfernen.
            try:
                await self.interaction.edit_original_response(view=None)
                logger.info(f"Buttons for leaderboard message {self.message.id} timed out and were removed.")
            except discord.NotFound:
                # Die Nachricht wurde bereits gelöscht, was in Ordnung ist.
                pass


class InfoCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info(f"{USER_PY_LOGGING_PREFIX} Cog initialisiert.")

    @app_commands.command(name="leaderboard", description="Zeigt das Server-Leaderboard an.")
    @app_commands.check(is_in_allowed_channels)
    async def leaderboard(self, interaction: discord.Interaction):
        """Zeigt das paginierte Leaderboard an."""
        await interaction.response.defer()

        leaderboard_data = await data_manager.get_server_leaderboard(str(interaction.guild.id))

        if not leaderboard_data:
            await interaction.followup.send("Für dieses Leaderboard sind noch keine Spieler gerankt.")
            return

        # Erstelle die View und rufe ihre start()-Methode auf.
        view = LeaderboardView(interaction, leaderboard_data)
        await view.start()


async def setup(bot: commands.Bot):
    """Fügt den InfoCommands Cog zum Bot hinzu."""
    await bot.add_cog(InfoCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen.")
