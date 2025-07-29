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

        server_id = str(interaction.guild.id)

        # Die Orchestrierungsfunktion aus data_manager aufrufen
        result = await data_manager.handle_riot_account_registration(
            server_id=server_id,
            game_name=game_name,
            tag_line=tag_line,
            region=region
        )

        if not result:
            message = f"Fehler bei der Registrierung von **{game_name}#{tag_line}**. Überprüfe die Eingabe oder versuche es später erneut."
        else:
            riot_account, status = result
            account_name = f"**{riot_account.game_name}#{riot_account.tag_line}**"
            
            if status == 'ADDED':
                message = f"✅ Erfolg! Der Account {account_name} wird jetzt auf diesem Server getrackt."
            elif status == 'ALREADY_EXISTS':
                message = f"ℹ️ Der Account {account_name} wird bereits auf diesem Server getrackt."
            else: # Sollte nicht passieren, aber als Fallback
                message = "Ein unerwarteter Fehler ist aufgetreten."

        await interaction.followup.send(message, ephemeral=True)


# Diese Async-Setup-Funktion ist erforderlich, damit der Cog vom Bot geladen werden kann
async def setup(bot: commands.Bot):
    """Fügt den TFTCommands Cog zum Bot hinzu."""
    await bot.add_cog(TFTCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen und registriert.")    