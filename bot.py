import discord 
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional
from logging_setup import setup_project_logger
import logging # Added for logger types
import sys # Added for logger fallback

load_dotenv()


# --- Logger Setup ---
logger: Optional[logging.Logger] = None
BOT_LOGGING_PREFIX = os.getenv("BOT_LOGGING_PREFIX", "BOT_")

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

try:
    import logging_setup
    logger = setup_project_logger(env_prefix="BOT_")
except ImportError:
    print(f"Error: Cannot find the 'logging_setup.py' module (for {BOT_LOGGING_PREFIX}). Using fallback logging.", file=sys.stderr)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - CARDS_FALLBACK - %(message)s')
    logger = logging.getLogger(f'{BOT_LOGGING_PREFIX}ImportFallback')
except Exception as e:
    print(f"Error during logging setup for {BOT_LOGGING_PREFIX}: {e}. Using fallback logging.", file=sys.stderr)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - CARDS_FALLBACK - %(message)s')
    logger = logging.getLogger(f'{BOT_LOGGING_PREFIX}SetupErrorFallback')

if logger is None: # Should ideally not be reached if fallbacks are robust
    logging.basicConfig(level=logging.CRITICAL, format='%(asctime)s - %(levelname)s - CARDS_CRITICAL_FALLBACK - %(message)s')
    logger = logging.getLogger('CardsCriticalFallback')
    logger.critical("Critical: Logger setup failed completely for cards.py.")
    # sys.exit("Critical logging setup failure in cards.py.") # Optional: exit if logging is absolutely essential

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user.name} (ID:{bot.user.id})')
    logger.info('Bot is ready and online')


if DISCORD_BOT_TOKEN is None:
    logger.error("CRITICAL: DISCORD_BOT_TOKEN not found. Make sure it's set in your .env file.")
else:
    try:
        logger.info("Attempting to connect to Discord...")
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("CRITICAL: Failed to log in. Check if your DISCORD_BOT_TOKEN is correct.")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during bot execution: {e}", exc_info=True)
        # exc_info=True will include traceback information in the log