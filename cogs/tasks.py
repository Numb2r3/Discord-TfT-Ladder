from discord.ext import tasks, commands
import logging
import asyncio
import data_manager
import database_crud as crud

from utils.checks import is_in_allowed_channels

USER_PY_LOGGING_PREFIX = "TASKS_COG_"

try:
    import logging_setup
    logger = logging_setup.setup_project_logger(env_prefix=USER_PY_LOGGING_PREFIX)
except ImportError:
    print(f"Error: Cannot find the 'logging_setup.py' module (for {USER_PY_LOGGING_PREFIX}).", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}Fallback') # Optional: Make fallback name more specific
except Exception as e:
    print(f"Error during logging setup for {USER_PY_LOGGING_PREFIX}: {e}. Using fallback.", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}SetupErrorFallback') # Optional: Make fallback name more specific

class BackgroundTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_all_ranks.start() # Starte den Task, wenn der Cog geladen wird

    def cog_unload(self):
        self.update_all_ranks.cancel() # Stoppe den Task, wenn der Cog entladen wird

    @tasks.loop(minutes=15)
    async def update_all_ranks(self):
        logger.info("BACKGROUND TASK: Triggering periodic rank update.")
        
        # EIN EINZIGER, SAUBERER AUFRUF
        try:
            # Wir fangen Fehler hier ab, um sie zu loggen
            await data_manager.handle_periodic_rank_update()
            logger.info("BACKGROUND TASK: Periodic rank update cycle finished.")
        except Exception as e:
            # Dieser Block fängt Fehler aus dem data_manager ab
            logger.error(f"BACKGROUND TASK: An unhandled exception occurred during the update process.", exc_info=e)


    @update_all_ranks.before_loop
    async def before_update_all_ranks(self):
        await self.bot.wait_until_ready()

    @update_all_ranks.error
    async def on_update_all_ranks_error(self, error: Exception):
        logger.error(f"BACKGROUND TASK: The update_all_ranks loop has crashed.", exc_info=error)
        # Optional: Hier könntest du versuchen, den Task neu zu starten.
        # self.update_all_ranks.restart()

async def setup(bot: commands.Bot):
    await bot.add_cog(BackgroundTasks(bot))