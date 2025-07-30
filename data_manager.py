import logging
import sys
import asyncio

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

async def sync_riot_account_by_riot_id(game_name: str, tag_line: str, region: str) -> RiotAccount | None:
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
    api_data = await api.get_account_by_riot_id(game_name, tag_line, region)
    
    if not api_data:
        logger.error(f"Could not retrieve Riot account data for {game_name}#{tag_line} from API.")
        return None
        
    # 2. Relevante Daten aus der API-Antwort extrahieren
    puuid = api_data.get('puuid')
    api_game_name = api_data.get('gameName')
    api_tag_line = api_data.get('tagLine')
    corrected_region = api_data.get('correctedRegion') 
    
    if not all([puuid, api_game_name, api_tag_line, corrected_region]): # corrected_region hinzugefügt
        logger.error("Incomplete data received from Riot API or missing corrected region.")
        return None


    # 3. Datenbank mit den neuen Daten aktualisieren oder neuen Account erstellen
    # Hier wird deine existierende CRUD-Funktion aufgerufen!
    loop = asyncio.get_running_loop()
    db_riot_account = await loop.run_in_executor(
        None,
        lambda: crud.add_or_update_riot_account(
            puuid=puuid,
            game_name=api_game_name,
            tag_line=api_tag_line,
            region=corrected_region
        )
    )
    
    if db_riot_account:
        logger.info(f"Successfully synced Riot account for PUUID {puuid} to database.")
    else:
        logger.error(f"Failed to sync Riot account for PUUID {puuid} to database.")
        
    return db_riot_account


async def sync_tft_rank_for_account(riot_account: RiotAccount) -> RiotAccountLPHistory | None:
    """
    Ruft die aktuellen Ranglistendaten für einen Riot Account ab und speichert sie in der History.
    """
    logger.info(f"Starting TFT rank sync for Riot account: {riot_account.game_name}")

    # 1. Ranglisten-Daten direkt mit der PUUID abrufen
    league_entries = await api.get_tft_league_entry_by_puuid(riot_account.puuid, riot_account.region)
    if not league_entries:
        logger.warning(f"No ranked TFT league entries found for PUUID {riot_account.puuid}.")
        return None

    ranked_tft_entry = next((entry for entry in league_entries if entry.get('queueType') == 'RANKED_TFT'), None)
    
    if not ranked_tft_entry:
        logger.info(f"No 'RANKED_TFT' queue entry found for PUUID {riot_account.puuid}.")
        return None

    # 2. Neuen History-Eintrag mit der CRUD-Funktion erstellen
    loop = asyncio.get_running_loop()
    new_history_entry = await loop.run_in_executor(
        None,
        lambda: crud.add_lp_history_entry(
            riot_account_id=riot_account.riot_account_id,
            queue_type=ranked_tft_entry.get('queueType'),
            league_points=ranked_tft_entry.get('leaguePoints'),
            tier=ranked_tft_entry.get('tier'),
            division=ranked_tft_entry.get('rank'),
            wins=ranked_tft_entry.get('wins'),
            losses=ranked_tft_entry.get('losses')
        )
    )

    if new_history_entry:
        logger.info(f"Successfully created new LP history entry for {riot_account.game_name}.")
    else:
        logger.error(f"Failed to create LP history entry for {riot_account.game_name}.")

    return new_history_entry

async def handle_server_activation(server_id: str, server_name: str, owner_id: str,owner_username: str) -> bool:
    """Orchestriert die Erstellung und Aktivierung eines Servers."""
    loop = asyncio.get_running_loop()

    discord_account_owner = await loop.run_in_executor(
        None,
        lambda: crud.add_or_update_discord_account(
            discord_user_id=owner_id,
            username=owner_username
        )
    )

    if not discord_account_owner:
        logger.error(f"Failed to create or update Discord account for owner {owner_id} on server {server_id}.")
        return 'ERROR' # Prozess abbrechen
    
    # Schritt 2: Sicherstellen, dass der Server in der DB existiert
    server_entry = await loop.run_in_executor(
        None,
        lambda: crud.add_or_update_server(server_id=server_id, server_name=server_name, owner_id=owner_id)
    )
    if not server_entry:
        logger.error(f"Failed to create or update server entry for server {server_id}.")
        return 'ERROR' # Prozess abbrechen

    activation_status = await loop.run_in_executor(
        None,
        lambda: crud.activate_server(server_id=server_id)
    )
    
    # Wenn die CRUD-Funktion None zurückgibt, war es ein Fehler, sonst der Status-String
    return activation_status if activation_status is not None else 'ERROR'

async def handle_riot_account_registration(server_id: str, game_name: str, tag_line: str, region: str) -> tuple[RiotAccount, str] | None:
    """
    Orchestriert die Registrierung eines Riot-Accounts zum Server-Tracking.
    Erstellt/updated den RiotAccount und verknüpft ihn mit dem Server.
    Gibt (RiotAccount, Status) zurück.
    """
    logger.info(f"Starting Riot account registration for {game_name}#{tag_line} on server {server_id}.")

    # --- Step 1: Get or Create the Riot Account ---
    riot_account = await sync_riot_account_by_riot_id(game_name, tag_line, region)
    if not riot_account:
        logger.error(f"Registration failed: Could not sync Riot account {game_name}#{tag_line}.")
        return None

    # --- Step 2: Link Riot Account to the Server for tracking ---
    loop = asyncio.get_running_loop()
    status = await loop.run_in_executor(
        None,
        lambda: crud.add_account_to_server(
            server_id=server_id,
            riot_account_id=riot_account.riot_account_id
        )
    )

    if not status:
        logger.error(f"Registration failed: Could not link Riot account to server for {game_name}#{tag_line}.")
        return None
    
    # --- Step 3: Return the result ---
    return riot_account, status

async def get_synced_rank_for_account(game_name: str, tag_line: str) -> tuple[RiotAccount, RiotAccountLPHistory] | str:
    """
    Sucht einen Riot Account in der DB, synchronisiert die neuesten LP-Daten
    und gibt den neuesten History-Eintrag zurück.
    Gibt 'NOT_FOUND' zurück, wenn der Account nicht in der DB ist.
    """
    # Schritt 1: Finde den Account in unserer DB
    loop = asyncio.get_running_loop()
    riot_account = await loop.run_in_executor(
        None,
        lambda: crud.get_riot_account_by_name(game_name, tag_line)
    )

    if not riot_account:
        return 'NOT_FOUND'

    # Schritt 2: Rufe die existierende Kernlogik auf, um die neuesten Daten zu holen und zu speichern
    live_lp_history = await sync_tft_rank_for_account(riot_account)
    if live_lp_history:
        # Fall A: Live-Sync war erfolgreich, gib die frischen Daten zurück
        return riot_account, live_lp_history
    else:
        # Fall B: Live-Sync schlug fehl. Hole die letzten Daten aus der DB.
        logger.warning(f"Live-Sync für {riot_account.game_name} fehlgeschlagen. Versuche Fallback auf DB-Daten.")
        fallback_lp_history = await loop.run_in_executor(
            None,
            lambda: crud.get_latest_lp_history(riot_account.riot_account_id)
        )
        
        if fallback_lp_history:
            # Erfolg: Gib den Account und die alten Daten zurück
            return riot_account, fallback_lp_history
        else:
            # Kein Fallback möglich
            return 'NO_HISTORY'
    
async def handle_periodic_rank_update():
    """
    Holt alle getrackten Accounts und synchronisiert deren Ranglisten-Daten.
    Diese Funktion ist für den Aufruf durch einen periodischen Task gedacht.
    """
    logger.info("DATA_MANAGER: Starting periodic rank update process.")
    loop = asyncio.get_running_loop()

    # Schritt 1: Alle Accounts aus der DB holen
    tracked_accounts = await loop.run_in_executor(None, crud.get_all_tracked_riot_accounts)
    
    if not tracked_accounts:
        logger.info("DATA_MANAGER: No tracked accounts found. Skipping periodic run.")
        return

    logger.info(f"DATA_MANAGER: Found {len(tracked_accounts)} accounts to update.")
    
    # Schritt 2: Durch alle Accounts iterieren und sie einzeln synchronisieren
    updated_count = 0
    for account in tracked_accounts:
        try:
            # Wir rufen die bereits existierende Funktion für einzelne Accounts auf
            result = await sync_tft_rank_for_account(account)
            if result:
                updated_count += 1
            # Die proaktive Pause gehört hierher, um die API-Aufrufe zu verteilen
            await asyncio.sleep(0.8) 
        except Exception as e:
            logger.error(f"DATA_MANAGER: Error updating rank for {account.puuid} during periodic task: {e}")

    logger.info(f"DATA_MANAGER: Finished periodic rank update. Successfully updated {updated_count}/{len(tracked_accounts)} accounts.")
