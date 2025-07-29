import logging
import sys

# Lokale Module importieren
import database_crud as crud
import riot_api_handler as api
from ORM_models import RiotAccount,  Player, PlayerRiotAccountLink, RiotAccountLPHistory
# --- Logging Setup ---
USER_PY_LOGGING_PREFIX = "MANAGER_"
try:
    import logging_setup 
    logger = logging_setup.setup_project_logger(env_prefix=USER_PY_LOGGING_PREFIX)
except ImportError:
    # Fallback, falls logging_setup nicht gefunden wird
    print(f"Error: Cannot find 'logging_setup.py' for {USER_PY_LOGGING_PREFIX}.", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}Fallback')
except Exception as e:
    print(f"Error during logging setup for {USER_PY_LOGGING_PREFIX}: {e}. Using fallback.", file=sys.stderr)
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - FALLBACK - %(message)s')
    logger = logging.getLogger(f'{USER_PY_LOGGING_PREFIX}SetupErrorFallback')

def sync_riot_account_by_riot_id(game_name: str, tag_line: str, region: str) -> RiotAccount | None:
    """
    Orchestriert den Prozess, einen Riot Account zu holen und in der DB zu speichern/aktualisieren.
    
    1. Fragt die Riot API nach Account-Daten.
    2. Nutzt CRUD-Funktionen, um den Account in der DB zu erstellen oder zu aktualisieren.
    
    Args:
        game_name: Der In-Game-Name des Spielers.
        tag_line: Die Tag-Line des Spielers (ohne #).
        region: Die Region des Spielers (z.B. 'euw1').

    Returns:
        Das RiotAccount-Objekt aus der Datenbank oder None bei einem Fehler.
    """
    logger.info(f"Starting sync for Riot account: {game_name}#{tag_line}")
    
    # 1. Daten von der Riot API abrufen
    api_data = api.get_account_by_riot_id(game_name, tag_line, region)
    
    if not api_data:
        logger.error(f"Could not retrieve Riot account data for {game_name}#{tag_line} from API.")
        return None
        
    # 2. Relevante Daten aus der API-Antwort extrahieren
    puuid = api_data.get('puuid')
    api_game_name = api_data.get('gameName')
    api_tag_line = api_data.get('tagLine')
    
    if not all([puuid, api_game_name, api_tag_line]):
        logger.error("Incomplete data received from Riot API.")
        return None
        
    # 3. Datenbank mit den neuen Daten aktualisieren oder neuen Account erstellen
    # Hier wird deine existierende CRUD-Funktion aufgerufen!
    db_riot_account = crud.add_or_update_riot_account(
        puuid=puuid,
        game_name=api_game_name,
        tag_line=api_tag_line,
        region=region 
    )
    
    if db_riot_account:
        logger.info(f"Successfully synced Riot account for PUUID {puuid} to database.")
    else:
        logger.error(f"Failed to sync Riot account for PUUID {puuid} to database.")
        
    return db_riot_account

def link_player_to_riot_account_by_id(player_id: str, riot_account_id: str, is_primary: bool = False) -> PlayerRiotAccountLink | None:
    """
    Verknüpft einen bestehenden Spieler mit einem bestehenden Riot Account.

    Args:
        player_id (str): Die ID des Spielers.
        riot_account_id (str): Die ID des Riot Accounts.
        is_primary (bool): Ob dies der primäre Riot Account des Spielers sein soll.

    Returns:
        Das PlayerRiotAccountLink-Objekt bei Erfolg, sonst None.
    """
    logger.info(f"Attempting to link player {player_id} to Riot account {riot_account_id}")

    # Rufe die CRUD-Funktion auf, um die Verknüpfung zu erstellen
    link = crud.link_player_to_riot_account(
        player_id=player_id,
        riot_account_id=riot_account_id,
        is_primary=is_primary
    )

def sync_tft_rank_for_account(riot_account: RiotAccount) -> RiotAccountLPHistory | None:
    """
    Ruft die aktuellen Ranglistendaten für einen Riot Account ab und speichert sie in der History.
    Dieser Prozess wurde durch die API-Änderung vereinfacht.
    """
    logger.info(f"Starting TFT rank sync for Riot account: {riot_account.game_name}")

    # 1. Ranglisten-Daten direkt mit der PUUID abrufen
    league_entries = api.get_tft_league_entry_by_puuid(riot_account.puuid, riot_account.region)
    if not league_entries:
        logger.warning(f"No ranked TFT league entries found for PUUID {riot_account.puuid}. Account might be unranked.")
        return None

    # Finde den relevanten Eintrag (normalerweise 'RANKED_TFT')
    ranked_tft_entry = None
    for entry in league_entries:
        if entry.get('queueType') == 'RANKED_TFT':
            ranked_tft_entry = entry
            break
    
    if not ranked_tft_entry:
        logger.info(f"No 'RANKED_TFT' queue entry found for PUUID {riot_account.puuid}.")
        return None

    # 2. Neuen History-Eintrag mit der CRUD-Funktion erstellen
    new_history_entry = crud.add_lp_history_entry(
        riot_account_id=riot_account.riot_account_id,
        queue_type=ranked_tft_entry.get('queueType'),
        league_points=ranked_tft_entry.get('leaguePoints'),
        tier=ranked_tft_entry.get('tier'),
        division=ranked_tft_entry.get('rank'), # In der API heißt es 'rank'
        wins=ranked_tft_entry.get('wins'),
        losses=ranked_tft_entry.get('losses')
    )

    if new_history_entry:
        logger.info(f"Successfully created new LP history entry for {riot_account.game_name}.")
    else:
        logger.error(f"Failed to create LP history entry for {riot_account.game_name}.")

    return new_history_entry

def register_new_player_with_riot_id(game_name: str, tag_line: str, region: str, player_display_name: str | None = None) -> tuple[Player, RiotAccount] | None:
    """
    Orchestrates the full registration of a new player using their Riot ID.
    
    This process involves:
    1. Fetching Riot Account data from the API and saving it to the database.
    2. Creating a new Player profile.
    3. Linking the Player profile to the Riot Account.

    Args:
        game_name: The player's in-game name.
        tag_line: The player's tag line.
        region: The player's region.
        player_display_name (optional): The initial display name for the player. 
                                        If None, the Riot game_name is used.

    Returns:
        A tuple containing the new Player and RiotAccount objects on success, otherwise None.
    """
    action_details = {'game_name': game_name, 'tag_line': tag_line, 'region': region}
    logger.info(f"Starting new player registration for {game_name}#{tag_line}.",
                extra={'action': 'PLAYER_REGISTRATION_START', **action_details})

    # --- Step 1: Get or Create the Riot Account ---
    # This uses an existing function to sync the account with the Riot API and our DB.
    riot_account = sync_riot_account_by_riot_id(game_name, tag_line, region)
    if not riot_account:
        logger.error("Player registration failed: Could not sync Riot account.",
                     extra={'action': 'PLAYER_REGISTRATION_FAIL_RIOT_SYNC', **action_details})
        return None

    # --- Step 2: Create the Player ---
    # If no specific display name is given, we use the Riot game name as a default.
    if riot_account.player_links:
        # The backref 'player_links' gives us the link objects. We get the player from the first active link.
        for link in riot_account.player_links:
            if link.is_active:
                existing_player = link.player
                logger.warning(f"Registration stopped: Riot account '{riot_account.game_name}' is already linked to player '{existing_player.display_name}'.",
                               extra={'action': 'PLAYER_REGISTRATION_ALREADY_LINKED', 'player_id': existing_player.player_id})
                return existing_player, riot_account # Return the existing player instead of creating a new one

    # --- Step 3: Create the Player (only if not linked) ---
    if player_display_name is None:
        player_display_name = riot_account.game_name

    new_player = crud.add_player(display_name=player_display_name)
    if not new_player:
        logger.error(f"Player registration failed: Could not create player profile for '{player_display_name}'.",
                     extra={'action': 'PLAYER_REGISTRATION_FAIL_ADD_PLAYER', **action_details})
        return None
    
    # --- Step 4: Link Player and Riot Account ---
    # We mark this first account as the primary one.
    link = crud.link_player_to_riot_account(
        player_id=new_player.player_id,
        riot_account_id=riot_account.riot_account_id,
        is_primary=True
    )

    if not link:
        # This is a critical failure, though unlikely if the previous steps succeeded.
        # We might want to consider rolling back the player creation in a real-world scenario.
        logger.critical(f"Player registration failed at the final linking step.",
                        extra={'action': 'PLAYER_REGISTRATION_FAIL_LINKING', 'player_id': new_player.player_id, 'riot_account_id': riot_account.riot_account_id})
        # For now, we'll signal failure. A more robust implementation could delete the created player.
        return None

    logger.info(f"Successfully registered new player '{new_player.display_name}' (ID: {new_player.player_id}) "
                f"and linked to Riot account '{riot_account.game_name}#{riot_account.tag_line}'.",
                extra={'action': 'PLAYER_REGISTRATION_SUCCESS', 'player_id': new_player.player_id})
    
    return new_player, riot_account