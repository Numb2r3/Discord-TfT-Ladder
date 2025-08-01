import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
import data_manager
from datetime import datetime, timezone

from utils.checks import is_in_allowed_channels

USER_PY_LOGGING_PREFIX = "TFT_COG_"
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
        super().__init__(timeout=180)  # Die Buttons verschwinden nach 3 Minuten
        self.interaction = interaction
        self.leaderboard_data = leaderboard_data
        self.current_page = 0
        self.items_per_page = 10

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
        total_pages = -(-len(self.leaderboard_data) // self.items_per_page) # Aufrunden
        embed.set_footer(text=f"Seite {self.current_page + 1} / {total_pages}")
        return embed

    async def update_message(self):
        """Aktualisiert die Nachricht mit der neuen Seite."""
        embed = await self.format_page()
        # Aktiviere/Deaktiviere Buttons basierend auf der Seite
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

# Fügen Sie den neuen Befehl zu Ihrer InfoCommands-Klasse hinzu
class InfoCommands(commands.Cog):
    # ... (__init__ und /registered-players bleiben unverändert) ...

    @app_commands.command(name="leaderboard", description="Zeigt das Server-Leaderboard an.")
    @app_commands.check(is_in_allowed_channels)
    async def leaderboard(self, interaction: discord.Interaction):
        """Zeigt das paginierte Leaderboard an."""
        # Schritt 1: Schiebe die Antwort privat auf. 
        # Das "is thinking..." ist nur für dich sichtbar.
        await interaction.response.defer(ephemeral=True)

        leaderboard_data = await data_manager.get_server_leaderboard(str(interaction.guild.id))

        if not leaderboard_data:
            # Sende eine private Fehlermeldung
            await interaction.followup.send("Für dieses Leaderboard sind noch keine Spieler gerankt.", ephemeral=True)
            return

        # Erstelle die View und sende die öffentliche Nachricht an den Kanal
        view = LeaderboardView(interaction, leaderboard_data)
        initial_embed = await view.format_page()
        view.prev_button.disabled = True
        view.next_button.disabled = (view.current_page + 1) * view.items_per_page >= len(leaderboard_data)

        # Sende die öffentliche Nachricht
        await interaction.followup.send(embed=initial_embed, delete_after=360, view=view) # 3600s = 1h

        # Schritt 2: Schließe die ursprüngliche Interaktion mit einer kleinen privaten Nachricht ab.
        #await interaction.followup.send("Das Leaderboard wurde im Kanal gepostet.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Fügt den InfoCommands Cog zum Bot hinzu."""
    await bot.add_cog(InfoCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen.")