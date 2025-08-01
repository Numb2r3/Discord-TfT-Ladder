import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
import data_manager
from datetime import datetime, timezone

from utils.checks import is_in_allowed_channels
import constants
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

class TFTCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info(f"{USER_PY_LOGGING_PREFIX} Cog initialisiert.") # Log, wenn der Cog initialisiert wird

    def _validate_and_correct_region(self,region_input: str | None) -> str:
        """
        Validiert und korrigiert die Regionseingabe des Benutzers.
        1. Prüft auf exakte Übereinstimmung.
        2. Prüft auf gängige Abkürzungen (z.B. 'euw' -> 'euw1').
        3. Gibt 'default' zurück, wenn nichts passt.
        """
        if not region_input:
            return 'default'
        
        region_lower = region_input.lower()

        if region_lower in constants.VALID_REGIONS:
            return region_lower
        
        if region_lower in constants.REGION_CORRECTIONS:
            return constants.REGION_CORRECTIONS[region_lower]
        
        return 'default'

    # Optional: Ein einfacher Listener, der beim Verbinden des Cogs ausgelöst wird
    @commands.Cog.listener()
    async def on_connect(self):
        logger.info(f"{USER_PY_LOGGING_PREFIX} hat sich mit Discord verbunden.")

    @app_commands.command(name="register", description="Registriert deinen Riot Account für TFT-Tracking.")
    @app_commands.check(is_in_allowed_channels)
    @app_commands.describe(
        game_name="Dein Riot Game Name (z.B. 'Der_Grosse_Spieler')",
        tag_line="Deine Tag Line (z.B. 'EUW' - OHNE #)",
        region="Deine Riot Region (z.B. 'euw1', 'na1', 'kr')"
    )
    async def register_riot_account(self, interaction: discord.Interaction, game_name: str, tag_line: str, region: str):
        """
        Registriert einen neuen Spieler und verknüpft ihn mit einem Riot Account.
        """
        logger.info(f"'{interaction.user.name}' versucht Riot Account '{game_name}#{tag_line}' in Region '{region}' zu registrieren.")

        region_to_save = self._validate_and_correct_region(region)
        display_region = "euw1 (Standard)" if region_to_save == 'default' else region_to_save
        
        # Zuerst eine temporäre Antwort senden, da die API-Anfrage etwas dauern kann
        await interaction.response.send_message(
            f"Versuche, Riot Account **{game_name}#{tag_line}** ({region}) zu registrieren...",
            ephemeral=True # Nur der Befehlsausführende sieht diese Nachricht
        )

        server_id = str(interaction.guild.id)

        # Die Orchestrierungsfunktion aus data_manager aufrufen
        result = await data_manager.handle_riot_account_registration(
            server_id=server_id,
            game_name=game_name,
            tag_line=tag_line,
            region=region_to_save
        )

        if not result:
            message = f"Fehler bei der Registrierung von **{game_name}#{tag_line}**. Überprüfe die Eingabe oder versuche es später erneut."
        else:
            riot_account, status = result
            account_name = f"**{riot_account.game_name}#{riot_account.tag_line}**"
            
            if status == 'ADDED':
                #message = f"✅ Erfolg! Der Account {account_name} wird jetzt auf diesem Server getrackt."
                embed = discord.Embed(
                title="We have a new competitor!",
                description=f"{account_name} joined!",
                color=discord.Color.green()
            )
                # Send without 'ephemeral=True' to make it visible to everyone
                await interaction.channel.send(embed=embed)
            elif status == 'ALREADY_EXISTS':
                message = f"ℹ️ Der Account {account_name} wird bereits auf diesem Server getrackt."
            else: # Sollte nicht passieren, aber als Fallback
                message = "Ein unerwarteter Fehler ist aufgetreten."

        await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="rank", description="Zeigt den aktuellen Rang eines getrackten Spielers an.")
    @app_commands.check(is_in_allowed_channels)
    @app_commands.describe(game_name="Der Riot Game Name", tag_line="Die Tag Line (ohne #)")
    async def rank(self, interaction: discord.Interaction, game_name: str, tag_line: str):
        """Fragt den aktuellen Rang ab, aktualisiert die DB und gibt ihn aus."""
        await interaction.response.defer(ephemeral=True)

        # EIN EINZIGER, SAUBERER AUFRUF an den data_manager
        result = await data_manager.get_synced_rank_for_account(
            server_id=str(interaction.guild.id), 
            game_name=game_name, 
            tag_line=tag_line
        )

        # Ergebnis auswerten

        if isinstance(result, str): # Prüft, ob ein Status-String wie 'NOT_FOUND' zurückkam
            if result == 'NOT_FOUND':
                message = f"Der Riot Account **{game_name}#{tag_line}** ist nicht registriert."
            else: # Fall 'NO_HISTORY' oder andere Fehler
                message = f"Für **{game_name}#{tag_line}** konnten keine Ranglisten-Daten gefunden werden."
        else:
            riot_account, lp_history_entry, server_rank_info = result
            
            account_name = f"**{riot_account.game_name}#{riot_account.tag_line}**"
            
            # --- NEUE FORMATIERUNG ---
            
            # Baue den Titel der Nachricht
            if server_rank_info:
                rank, total = server_rank_info
                title = f"Rang {rank}/{total} für {account_name}:"
            else:
                # Fallback, falls der Spieler keinen Server-Rang hat
                title = f"Rang für {account_name}:"

            # Baue den Rest der Nachricht
            details = (
                f"> **{lp_history_entry.tier.capitalize()} {lp_history_entry.division}**\n"
                f"> **{lp_history_entry.league_points} LP**\n"
                f"> Wins: {lp_history_entry.wins} | Losses: {lp_history_entry.losses}"
            )
            
            message = f"{title}\n{details}"

            # Logik für veraltete Daten bleibt gleich
            now_utc = datetime.now(timezone.utc)
            data_age = now_utc - lp_history_entry.retrieved_at.replace(tzinfo=timezone.utc)
            if data_age.total_seconds() > 300:
                timestamp_discord = f"<t:{int(lp_history_entry.retrieved_at.timestamp())}:R>"
                message += f"\n\n*Achtung: Die Daten sind nicht live (Stand: {timestamp_discord}).*"

        await interaction.followup.send(message, ephemeral=True)

# Diese Async-Setup-Funktion ist erforderlich, damit der Cog vom Bot geladen werden kann
async def setup(bot: commands.Bot):
    """Fügt den TFTCommands Cog zum Bot hinzu."""
    await bot.add_cog(TFTCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen und registriert.")    