import requests
import os
import logging
from dotenv import load_dotenv
import time
from collections import deque # KORREKTUR: Fehlender Import hinzugefügt
from threading import Lock

load_dotenv()

# --- Konfiguration ---

USER_PY_LOGGING_PREFIX = "RIOT_API_"
GIST_RAW_URL = os.getenv("RIOT_API_GIST")
MAX_RETRIES = 3

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

def parse_rate_limits(limits_str: str | None) -> list[tuple[int, int]]:
    """
    Parst einen String wie "20:1,100:120" in eine Liste von Tuples.
    Fällt auf Standardwerte zurück, wenn die Variable nicht gesetzt oder fehlerhaft ist.
    """
    default_limits = [(20, 1), (100, 120)]
    if not limits_str:
        logger.warning("RIOT_API_LIMITS not set in .env, using default values: %s", default_limits)
        return default_limits
    
    parsed_limits = []
    try:
        pairs = limits_str.split(',')
        for pair in pairs:
            count, period = map(int, pair.strip().split(':'))
            parsed_limits.append((count, period))
        logger.info("Loaded rate limits from .env: %s", parsed_limits)
        return parsed_limits
    except (ValueError, IndexError) as e:
        logger.error("Failed to parse RIOT_API_LIMITS='%s'. Error: %s. Using default values: %s",
                     limits_str, e, default_limits)
        return default_limits
    
RIOT_API_LIMITS_STR = os.getenv("RIOT_API_LIMITS")
RATE_LIMITS = parse_rate_limits(RIOT_API_LIMITS_STR)

RIOT_ROUTING = {
    'americas': ['br1', 'la1', 'la2', 'na1'],
    'asia': ['jp1', 'kr','oc1','sg2','tw2','vn2'],
    'europe': ['eun1', 'euw1', 'tr1', 'ru','me1'],
    'esports':['esports']
}
    
# --- Intelligente, Thread-sichere Rate Limiter Klasse ---
class RateLimiter:
    """
    Eine Klasse zur proaktiven und Thread-sicheren Verwaltung von API-Rate-Limits.
    Sie berücksichtigt mehrere Zeitfenster gleichzeitig.
    """
    def __init__(self, limits):
        """
        Initialisiert den Rate Limiter.
        
        Args:
            limits (list of tuples): Eine Liste von Limits, z.B. [(Anzahl, Sekunden), ...].
        """
        self.limits = sorted(limits, key=lambda x: x[1])
        self.history = [deque() for _ in self.limits]
        self.lock = Lock()

    def acquire(self):
        """
        Blockiert, bis eine Anfrage sicher gesendet werden kann, und reserviert dann den Slot.
        """
        with self.lock:
            while True:
                now = time.time()
                wait_duration = 0

                for i, (count, period) in enumerate(self.limits):
                    while self.history[i] and self.history[i][0] <= now - period:
                        self.history[i].popleft()
                    
                    if len(self.history[i]) >= count:
                        time_to_wait = self.history[i][0] + period - now
                        if time_to_wait > wait_duration:
                            wait_duration = time_to_wait
                
                if wait_duration > 0:
                    logger.debug(f"Rate limit active. Waiting for {wait_duration:.2f}s.")
                    time.sleep(wait_duration + 0.01)
                    continue
                else:
                    for i in range(len(self.limits)):
                        self.history[i].append(now)
                    break

# Erstelle eine Instanz des RateLimiters mit den (aus der .env) geladenen Limits
riot_rate_limiter = RateLimiter(RATE_LIMITS)

def _get_latest_api_key() -> str |None:
    try:
        response = requests.get(GIST_RAW_URL, timeout=10)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            logger.error(f"Could not fetch API key from Gist. Status code: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Network error while fetching API key from Gist: {e}")
        return None
    
def _get_routing_value(region:str) -> str |None:
    for route, platforms in RIOT_ROUTING.items():
        if region.lower() in platforms:
            return route
    logger.error(f"Could not find a routing value for region: {region}")
    return None

def _make_api_request(url: str) -> dict | list | None:
    """Führt eine Anfrage an die Riot-API aus, fügt den API-Schlüssel hinzu und behandelt Fehler."""
    api_key = _get_latest_api_key()
    if not api_key:
        logger.critical("Cannot make API request without an API key.")
        return None
    
    headers = {"X-Riot-Token": api_key}
    time.sleep(1.2)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 429:
            logger.warning("Rate limit exceeded. Waiting for a moment...")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP Error for URL {url}: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request Exception for URL {url}: {req_err}")
    return None

def get_account_by_riot_id(game_name: str, tag_line: str, region: str) -> dict | None:
    """Fragt die Riot API nach einem Account anhand der Riot ID und der Region ab."""
    logger.info(f"Querying Riot account for {game_name}#{tag_line} in region {region}")
    routing_value = _get_routing_value(region)
    if not routing_value:
        return None
    
    url = f"https://{routing_value}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    return _make_api_request(url)

def get_tft_league_entry_by_puuid(puuid: str, region: str) -> list[dict] | None:
    """
    Fragt die TFT-API nach den Ranglisten-Einträgen eines Spielers direkt über die PUUID ab.
    """
    logger.info(f"Querying TFT league entry for PUUID {puuid} in region {region}")
    # Der Endpunkt wurde von .../by-summoner/{summonerId} auf .../by-puuid/{puuid} geändert
    url = f"https://{region}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
    return _make_api_request(url)
    
def get_tft_match_ids_by_puuid(puuid: str, region: str, count: int = 20) -> list[str] | None:
    """Fragt die letzten Match-IDs eines Spielers anhand seiner PUUID ab."""
    logger.info(f"Querying last {count} TFT match IDs for PUUID {puuid} in region {region}")
    routing_value = _get_routing_value(region)
    if not routing_value:
        return None
        
    url = f"https://{routing_value}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    return _make_api_request(url)

def get_tft_match_details(match_id: str, region: str) -> dict | None:
    """Fragt die Details zu einem spezifischen Match anhand der Match-ID ab."""
    logger.info(f"Querying TFT match details for match ID {match_id} in region {region}")
    routing_value = _get_routing_value(region)
    if not routing_value:
        return None
        
    url = f"https://{routing_value}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    return _make_api_request(url)