import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
import data_manager

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

class TFTCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info(f"{USER_PY_LOGGING_PREFIX} Cog initialisiert.") # Log, wenn der Cog initialisiert wird

    # Optional: Ein einfacher Listener, der beim Verbinden des Cogs ausgelöst wird
    @commands.Cog.listener()
    async def on_connect(self):
        logger.info(f"{USER_PY_LOGGING_PREFIX} hat sich mit Discord verbunden.")

    @app_commands.command(name="register", description="Registriert deinen Riot Account für TFT-Tracking.")
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

        # Zuerst eine temporäre Antwort senden, da die API-Anfrage etwas dauern kann
        await interaction.response.send_message(
            f"Versuche, Riot Account **{game_name}#{tag_line}** ({region}) zu registrieren...",
            ephemeral=True # Nur der Befehlsausführende sieht diese Nachricht
        )

        # Die Orchestrierungsfunktion aus data_manager aufrufen
        player_riot_account_tuple = await data_manager.register_new_player_with_riot_id(
            game_name=game_name,
            tag_line=tag_line,
            region=region
        )

        if player_riot_account_tuple:
            player, riot_account = player_riot_account_tuple
            success_message = (
                f"Dein Riot Account **{riot_account.game_name}#{riot_account.tag_line}** "
                f"wurde erfolgreich als Spieler **'{player.display_name}'** registriert und verknüpft!"
            )
            logger.info(f"Registrierung erfolgreich für Spieler '{player.display_name}' ({player.player_id}).")
            await interaction.followup.send(success_message, ephemeral=True) # followup, da bereits geantwortet wurde
        else:
            error_message = (
                f"Fehler bei der Registrierung von **{game_name}#{tag_line}**."
                "Bitte überprüfe den Namen, die Tag Line und die Region. "
                "Es könnte auch ein Problem mit der Riot API vorliegen oder der Account ist bereits verknüpft."
            )
            logger.error(f"Registrierung fehlgeschlagen für '{game_name}#{tag_line}'.")
            await interaction.followup.send(error_message, ephemeral=True)


# Diese Async-Setup-Funktion ist erforderlich, damit der Cog vom Bot geladen werden kann
async def setup(bot: commands.Bot):
    """Fügt den TFTCommands Cog zum Bot hinzu."""
    await bot.add_cog(TFTCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen und registriert.")    