import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import sys

load_dotenv()


# --- Logger Setup ---

BOT_LOGGING_PREFIX = "DISCORD_BOT_"
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

try:
    import logging_setup 
    logger = logging_setup.setup_project_logger(env_prefix=BOT_LOGGING_PREFIX)
except ImportError:
    print(f"Error: Cannot find the 'logging_setup.py' module (for {BOT_LOGGING_PREFIX}).", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{BOT_LOGGING_PREFIX}Fallback') # Optional: Make fallback name more specific
except Exception as e:
    print(f"Error during logging setup for {BOT_LOGGING_PREFIX}: {e}. Using fallback.", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{BOT_LOGGING_PREFIX}SetupErrorFallback') # Optional: Make fallback name more specific

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user.name} (ID:{bot.user.id})')
    logger.info('Bot is ready and online')


# --- Bot Commands ---
@bot.command(name='ping')
async def ping(ctx: commands.Context):
    """A simple test command that replies with Pong!"""
    logger.info(f"Received !ping command from {ctx.author.name}")
    await ctx.reply("Pong!")


# --- Run the Bot ---
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logger.critical("FATAL: DISCORD_BOT_TOKEN is not set in the .env file.")
    else:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.errors.LoginFailure:
            logger.critical("FATAL: Failed to log in. Is the DISCORD_BOT_TOKEN correct?")
        except Exception as e:
            logger.critical(f"An unexpected error occurred: {e}")
