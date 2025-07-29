# test_registration.py

import logging
import sys

# Import the main function we want to test
from data_manager import register_new_player_with_riot_id

# Import necessary components for database setup
from sql_functions import get_engine_and_session_factory
from ORM_models import Base

# --- Basic Logging Setup for the Test ---
# This helps see what's happening in the imported modules.
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("REGISTRATION_TEST")


def setup_database():
    """
    Ensures that all tables are created in the database.
    """
    log.info("Setting up database...")
    try:
        # Get the engine from our centralized function
        engine, _ = get_engine_and_session_factory()
        
        # This command creates all tables defined in ORM_models.py if they don't exist.
        # It is safe to run this multiple times.
        Base.metadata.create_all(engine)
        
        log.info("Database setup complete. Tables are ready.")
    except Exception as e:
        log.error(f"An error occurred during database setup: {e}")
        # Exit if we can't even connect to the DB
        sys.exit(1)


def run_test():
    """
    Main function to run the registration test.
    """
    # --- CONFIGURE YOUR TEST DATA HERE ---
    TEST_GAME_NAME = "Schmiery"  # <-- CHANGE THIS
    TEST_TAG_LINE = "SMIRI"          # <-- CHANGE THIS
    TEST_REGION = "euw1"            # <-- CHANGE THIS
    # -------------------------------------

    if "YourRiotName" in TEST_GAME_NAME:
        log.warning("Please update the TEST_GAME_NAME, TEST_TAG_LINE, and TEST_REGION in the script before running.")
        return

    log.info(f"Attempting to register player: {TEST_GAME_NAME}#{TEST_TAG_LINE}")

    try:
        # Call the function we want to test
        result = register_new_player_with_riot_id(
            game_name=TEST_GAME_NAME,
            tag_line=TEST_TAG_LINE,
            region=TEST_REGION
        )

        # Check the result
        if result:
            new_player, riot_account = result
            log.info("✅ --- REGISTRATION SUCCESSFUL --- ✅")
            log.info(f"  -> Created Player: {new_player}")
            log.info(f"  -> Synced Riot Account: {riot_account}")
        else:
            log.error("❌ --- REGISTRATION FAILED --- ❌")
            log.error("  -> The function returned None. Check the logs above for specific errors from the data_manager or crud modules.")

    except Exception as e:
        log.error(f"An unexpected error occurred during the test: {e}", exc_info=True)


if __name__ == "__main__":
    # This block runs when you execute the script directly
    setup_database()
    run_test()