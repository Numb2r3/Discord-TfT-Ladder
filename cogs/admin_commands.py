import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
import data_manager

USER_PY_LOGGING_PREFIX = "ADMIN_COG_"

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


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info(f"{USER_PY_LOGGING_PREFIX} Cog initialisiert.")
    @app_commands.command(name="activate-server", description="Aktiviert diesen Server für alle Bot-Features.")
    @app_commands.checks.has_permissions(administrator=True) # SICHERHEIT: Nur der Serveradmin kann diesen Befehl nutzen
    async def activate_server(self, interaction: discord.Interaction):

        """Aktiviert den Server, auf dem der Befehl ausgeführt wird."""
        server_id = str(interaction.guild.id)
        server_name = interaction.guild.name
        owner_id = str(interaction.guild.owner_id)
        owner_username = interaction.user.name

        await interaction.response.defer(ephemeral=True) # Wir brauchen etwas Zeit für die DB

        status = await data_manager.handle_server_activation(
            server_id=server_id, 
            server_name=server_name, 
            owner_id=owner_id, 
            owner_username=owner_username
        )

        # Den Status auswerten, um die richtige Nachricht zu senden
        if status == 'ACTIVATED':
            message = f"✅ Server '{server_name}' wurde erfolgreich aktiviert und kann nun alle Features nutzen!"
            logger.info(f"Server '{server_name}' ({server_id}) wurde vom Admin aktiviert.")
        elif status == 'ALREADY_ACTIVE':
            message = f"ℹ️ Server '{server_name}' ist bereits aktiv. Es wurde nichts geändert."
            logger.info(f"Erneuter Aktivierungsversuch für bereits aktiven Server '{server_name}'.")
        else: # Beinhaltet 'ERROR', 'NOT_FOUND' und None
            message = "Ein interner Fehler ist aufgetreten. Die Aktivierung konnte nicht durchgeführt werden."
            logger.error(f"Fehler bei der Aktivierung von Server '{server_name}' ({server_id}). Status: {status}")
        
        await interaction.followup.send(message)

    # Optional: Fehlerbehandlung für den is_owner-Check
    @activate_server.error
    async def on_activate_server_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Du benötigst Administrator-Rechte, um diesen Befehl auszuführen.", ephemeral=True)
        else:
            logger.error(f"Unerwarteter Fehler im activate-server Befehl: {error}")
            await interaction.response.send_message("Ein unerwarteter Fehler ist aufgetreten.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Fügt den AdminCommands Cog zum Bot hinzu."""
    await bot.add_cog(AdminCommands(bot))
    logger.info(f"{USER_PY_LOGGING_PREFIX} Cog erfolgreich geladen und registriert.")
