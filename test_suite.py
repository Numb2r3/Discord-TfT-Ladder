import unittest
import logging
import sys
from sqlalchemy.orm import joinedload, exc as orm_exc

# --- Import all the components we need to test ---
import database_crud as crud
from data_manager import register_new_player_with_riot_id
from sql_functions import get_engine_and_session_factory
from ORM_models import Base, Player, RiotAccount, PlayerRiotAccountLink

# --- Basic Logging Setup for the Test ---
# This helps see what's happening in the imported modules.
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("TEST_SUITE")


class TestDatabaseAndRegistration(unittest.TestCase):
    """
    A full test suite for the database and registration logic.
    This class uses the standard `unittest` framework.
    """
    
    # --- Test Data ---
    TEST_GAME_NAME = "Schmiery"  # <-- CHANGE THIS
    TEST_TAG_LINE = "SMIRI"         # <-- CHANGE THIS
    TEST_REGION = "euw1"           # <-- CHANGE THIS

    @classmethod
    def setUpClass(cls):
        """
        This method runs ONCE before any tests in this class.
        It's used to set up the database connection and tables.
        """
        print("="*70)
        print("INITIALIZING TEST SUITE: Setting up the database...")
        print("="*70)
        if "YourRiotName" in cls.TEST_GAME_NAME:
            log.error("Please update the TEST_GAME_NAME, TEST_TAG_LINE, and TEST_REGION in the test_suite.py script before running.")
            sys.exit("Stopping tests: Please configure test data first.")

        cls.engine, _ = get_engine_and_session_factory()
        Base.metadata.drop_all(cls.engine) # Start with a clean slate
        Base.metadata.create_all(cls.engine)
        log.info("Database setup complete.")

    def tearDown(self):
        """
        This method runs AFTER EACH test.
        It cleans up the database to ensure tests are independent.
        """
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def test_01_full_registration_new_player(self):
        """
        Tests the complete registration workflow for a brand new player.
        This is the most critical end-to-end test.
        """
        print("\n" + "="*70)
        print("RUNNING: test_01_full_registration_new_player")
        print("="*70)
        
        # Action: Call the main registration function
        result = register_new_player_with_riot_id(
            game_name=self.TEST_GAME_NAME,
            tag_line=self.TEST_TAG_LINE,
            region=self.TEST_REGION
        )

        # Assertions: Check if the result is what we expect
        self.assertIsNotNone(result, "Registration function should not return None for a new player.")
        
        player, riot_account = result
        self.assertIsInstance(player, Player)
        self.assertIsInstance(riot_account, RiotAccount)
        self.assertEqual(player.display_name, riot_account.game_name)
        print("✅ PASSED: New player registration successful.")

    def test_02_registration_for_existing_player(self):
        """
        Tests that trying to register the SAME player again does NOT create a duplicate.
        It should return the existing player profile.
        """
        print("\n" + "="*70)
        print("RUNNING: test_02_registration_for_existing_player")
        print("="*70)

        # Setup: First, register the player once.
        register_new_player_with_riot_id(self.TEST_GAME_NAME, self.TEST_TAG_LINE, self.TEST_REGION)

        # Action: Register the exact same player again.
        result_again = register_new_player_with_riot_id(self.TEST_GAME_NAME, self.TEST_TAG_LINE, self.TEST_REGION)

        # Assertions
        self.assertIsNotNone(result_again)
        
        # Check that we only have ONE player in the database.
        with crud.session_scope() as session:
            player_count = session.query(Player).count()
            self.assertEqual(player_count, 1, "Should not create a duplicate player.")
        
        print("✅ PASSED: Duplicate registration correctly handled.")

    def test_03_eager_loading_prevents_detached_error(self):
        """
        Tests that our `load_options` fix works correctly.
        It gets a player with eager loading and accesses relationships AFTER the session is closed.
        """
        print("\n" + "="*70)
        print("RUNNING: test_03_eager_loading_prevents_detached_error")
        print("="*70)

        # Setup: Create a player and a linked riot account.
        player = crud.add_player("TestEager")
        riot_account = crud.add_or_update_riot_account("EAGER_PUUID", "EagerName", "EAG", "euw1")
        crud.link_player_to_riot_account(player.player_id, riot_account.riot_account_id)

        # Action: Get the Riot account using the function with our fix.
        retrieved_account = crud.add_or_update_riot_account("EAGER_PUUID", "EagerName", "EAG", "euw1")

        # Assertion: Try to access the relationship. If this works, the test passes.
        self.assertEqual(len(retrieved_account.player_links), 1)
        self.assertEqual(retrieved_account.player_links[0].player.display_name, "TestEager")
        print("✅ PASSED: Eager loading works, no DetachedInstanceError occurred.")

    def test_04_lazy_loading_still_causes_detached_error(self):
        """
        Tests that the DetachedInstanceError STILL happens when we DON'T use eager loading.
        This confirms our understanding of the problem and the solution.
        """
        print("\n" + "="*70)
        print("RUNNING: test_04_lazy_loading_still_causes_detached_error")
        print("="*70)
        
        # Setup
        crud.add_or_update_riot_account("LAZY_PUUID", "LazyName", "LAZ", "euw1")
        
        # Action: Get the account using a function WITHOUT eager loading options.
        retrieved_account = crud.get_riot_account_by_puuid(puuid="LAZY_PUUID")

        # Assertion: We EXPECT a DetachedInstanceError here.
        with self.assertRaises(orm_exc.DetachedInstanceError):
            _ = retrieved_account.player_links 

        print("✅ PASSED: DetachedInstanceError occurred as expected.")


if __name__ == '__main__':
    # This allows you to run the tests by executing `python test_suite.py`
    unittest.main()