import time
from datetime import datetime, timedelta

# --- First, ensure the database exists ---
# Note: In a real application, you might run create_db.py separately.
# For this test script, we call it directly to ensure a clean start.
from create_db import create_database_tables
print("--- [Step 0] Ensuring database and tables exist ---")
create_database_tables()
print("--- Database check complete ---\n")

# --- Now, import all the functions we want to test ---
import database_crud as crud

def run_full_test():
    """
    Runs a comprehensive test of all major CRUD functions.
    """
    print("--- [Step 1] Creating a new Player ---")
    player1 = crud.add_player(display_name="TestPlayer1")
    if player1:
        print(f"SUCCESS: Created Player -> ID: {player1.player_id}, Name: {player1.display_name}\n")
    else:
        print("FAILURE: Could not create Player.\n")
        return # Stop the test if this fails

    print("--- [Step 2] Creating a new Riot Account ---")
    riot_account1_puuid = "TEST_PUUID_12345"
    riot_account1 = crud.add_or_update_riot_account(
        puuid=riot_account1_puuid,
        game_name="InitialName",
        tag_line="EUW",
        region="euw1"
    )
    if riot_account1:
        print(f"SUCCESS: Created Riot Account -> ID: {riot_account1.riot_account_id}, Name: {riot_account1.game_name}#{riot_account1.tag_line}\n")
    else:
        print("FAILURE: Could not create Riot Account.\n")
        return

    print("--- [Step 3] Linking Player to Riot Account ---")
    link1 = crud.link_player_to_riot_account(player1.player_id, riot_account1.riot_account_id)
    if link1:
        print(f"SUCCESS: Linked Player and Riot Account. Link ID: {link1.link_id}, Active: {link1.is_active}\n")
    else:
        print("FAILURE: Could not link accounts.\n")

    print("--- [Step 4] Updating Player and Riot Account Names (Testing History) ---")
    update_player_success = crud.update_player_display_name(player1.player_id, "TestPlayer1_Updated", "TEST_RUNNER")
    print(f"Player name update status: {'SUCCESS' if update_player_success else 'FAILURE'}")

    # Wait a second to see a different timestamp in the history
    time.sleep(1)

    updated_riot_account = crud.add_or_update_riot_account(
        puuid=riot_account1_puuid,
        game_name="UpdatedName",
        tag_line="EUW",
        region="euw1"
    )
    if updated_riot_account and updated_riot_account.game_name == "UpdatedName":
        print(f"Riot Account name update status: SUCCESS. New name: {updated_riot_account.game_name}\n")
    else:
        print("Riot Account name update status: FAILURE\n")

    print("--- [Step 5] Deactivating and Re-activating a Link ---")
    deactivate_success = crud.deactivate_riot_link(player1.player_id, riot_account1.riot_account_id)
    print(f"Deactivation status: {'SUCCESS' if deactivate_success else 'FAILURE'}")

    # Try to re-link, which should create a new, active link
    relink_success = crud.link_player_to_riot_account(player1.player_id, riot_account1.riot_account_id)
    if relink_success:
        print(f"Re-linking status: SUCCESS. New Link ID: {relink_success.link_id}, Active: {relink_success.is_active}\n")
    else:
        print("Re-linking status: FAILURE\n")

    print("--- [Step 6] Server and Race Setup ---")
    server1_id = "TEST_SERVER_ID_98765"
    server1 = crud.add_or_update_server(server_id=server1_id, server_name="Test Server")
    if server1:
        print(f"SUCCESS: Created Server -> ID: {server1.server_id}")
    else:
        print("FAILURE: Could not create Server.")
        return

    server_player1 = crud.add_player_to_server(player1.player_id, server1.server_id)
    if server_player1:
        print(f"SUCCESS: Added Player to Server -> ServerPlayer ID: {server_player1.server_player_id}")
    else:
        print("FAILURE: Could not add player to server.")
        return

    race1 = crud.create_race(
        server_id=server1.server_id,
        name="Summer LP Climb",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=7),
        race_type="LP_CLIMB"
    )
    if race1:
        print(f"SUCCESS: Created Race -> ID: {race1.race_id}, Name: {race1.race_name}")
    else:
        print("FAILURE: Could not create race.")
        return

    participant1 = crud.add_participant_to_race(race1.race_id, server_player1.server_player_id, starting_value=100)
    if participant1:
        print(f"SUCCESS: Added Participant to Race -> Participant ID: {participant1.participant_id}, Start Value: {participant1.starting_value}\n")
    else:
        print("FAILURE: Could not add participant to race.\n")

    print("--- All tests completed. ---")


if __name__ == "__main__":
    run_full_test()