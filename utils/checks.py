import discord
import os
import logging
import sys # <-- Hinzugefügt für sys.stderr

USER_PY_LOGGING_PREFIX = "UTILS_CHECK_"

try:
    import logging_setup
    logger = logging_setup.setup_project_logger(env_prefix=USER_PY_LOGGING_PREFIX)
except ImportError:
    print(f"Error: Cannot find the 'logging_setup.py' module (for {USER_PY_LOGGING_PREFIX}).", file=sys.stderr)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}Fallback')
except Exception as e:
    print(f"Error during logging setup for {USER_PY_LOGGING_PREFIX}: {e}. Using fallback.", file=sys.stderr)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}SetupErrorFallback')


# --- Lade die Liste der erlaubten Kanal-IDs ---
ALLOWED_CHANNEL_IDS = []
ids_str = os.getenv("ALLOWED_COMMAND_CHANNEL_IDS")

if ids_str:
    try:
        ALLOWED_CHANNEL_IDS = [int(channel_id.strip()) for channel_id in ids_str.split(',')]
        logger.info(f"Successfully loaded {len(ALLOWED_CHANNEL_IDS)} allowed channel ID(s): {ALLOWED_CHANNEL_IDS}")
    except (ValueError, TypeError):
        logger.error("Could not parse ALLOWED_COMMAND_CHANNEL_IDS. Ensure it is a comma-separated list of numbers.")
else:
    logger.warning("No ALLOWED_COMMAND_CHANNEL_IDS found in .env. Commands will be allowed in all channels.")

# --- Die zentrale Prüffunktion (Check) ---
async def is_in_allowed_channels(interaction: discord.Interaction) -> bool:
    """
    Prüft, ob der Befehl in einem der erlaubten Kanäle ausgeführt wird.
    Kann von jedem Cog importiert werden.
    """
    # Logge den Versuch, den Befehl auszuführen
    # Dies ist nützlich, um zu sehen, wer welche Befehle wann und wo versucht
    logger.info(
        f"User '{interaction.user}' (ID: {interaction.user.id}) initiated command "
        f"/{interaction.command.name} in channel #{interaction.channel.name} (ID: {interaction.channel.id})."
    )

    # Wenn die Liste leer ist, erlaube den Befehl überall
    if not ALLOWED_CHANNEL_IDS:
        logger.debug("Check PASSED (by default): No allowed channels are configured.")
        return True 

    # Prüfe, ob die Kanal-ID in der Liste ist
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        # NEUE LOGIK: Finde die erlaubten Kanäle, die auf DIESEM Server existieren.
        guild_channel_ids = [c.id for c in interaction.guild.channels]
        relevant_allowed_channels = [ch_id for ch_id in ALLOWED_CHANNEL_IDS if ch_id in guild_channel_ids]

        # Erstelle die Fehlermeldung basierend auf den relevanten Kanälen.
        if not relevant_allowed_channels:
            message = "Dieser Befehl kann auf diesem Server in keinem Kanal ausgeführt werden."
        else:
            allowed_mentions = ", ".join([f"<#{_id}>" for _id in relevant_allowed_channels])
            message = f"Diesen Befehl kannst du nur in den folgenden Kanälen verwenden: {allowed_mentions}"

        logger.warning(
            f"Check FAILED for user {interaction.user.id}. "
            f"Channel {interaction.channel.id} is not in the allowed list."
        )
        await interaction.response.send_message(message, ephemeral=True)
        return False

    logger.debug(f"Check PASSED for user {interaction.user.id}. Channel {interaction.channel.id} is allowed.")
    return True