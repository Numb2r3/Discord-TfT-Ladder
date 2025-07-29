import discord
from discord.ext import commands
from discord import app_commands # Import for slash commands
import logging
import sys

USER_PY_LOGGING_PREFIX = "GENERAL_COG_" # Ein eindeutiger Präfix für diesen Cog
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

# Cogs are classes that group commands, listeners, and state
class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # A simple listener example within a cog
    @commands.Cog.listener()
    async def on_connect(self):
        print("General Cog has connected to Discord.")

    # This is now a slash command. The user will type /ping
    @app_commands.command(name="ping", description="Replies with Pong!")
    async def ping(self, interaction: discord.Interaction):
        """A simple test slash command that replies with Pong!"""
        # 'interaction.response.send_message' is how you reply to slash commands
        # 'ephemeral=True' makes the reply visible only to the user who ran the command
        await interaction.response.send_message("Pong!", ephemeral=True)


# This async setup function is required for the cog to be loaded by the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))