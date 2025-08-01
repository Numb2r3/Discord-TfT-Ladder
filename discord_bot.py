import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import sys

load_dotenv()


# --- Logger Setup ---

BOT_LOGGING_PREFIX = "DISCORD_BOT_"
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

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents) # Prefix isn't used for slash commands but is required

    async def setup_hook(self):
        """This is called when the bot logs in, to load cogs."""
        logger.info("--- Loading Cogs ---")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Successfully loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog_name}: {e}")
        
        # This syncs the slash commands to Discord.
        # You can specify a guild_id to make updates instant during testing.
        #GUILD_ID = discord.Object(id=os.getenv("DISCORD_GUILD_ID")) # Optional: Add your server ID to .env
        #self.tree.copy_global_to(guild=GUILD_ID)
        #await self.tree.sync(guild=GUILD_ID)
        await self.tree.sync() # Sync globally

        async def on_ready(self):
            """Event that runs when the bot is ready."""
            logger.info(f'Bot logged in as {self.user.name} (ID:{self.user.id})')
            logger.info('Bot is ready and online')
            print("------")

bot = MyBot()




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
