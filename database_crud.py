import uuid
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
import logging
from datetime import datetime


# --- Local Imports ---
from ORM_models import (
    Base, Player, PlayerDisplayNameHistory, DiscordAccount,
    PlayerDiscordAccountLink, RiotAccount, RiotAccountNameHistory,

    PlayerRiotAccountLink, DiscordServer, ServerPlayer, Race, RaceParticipant
)
from sql_functions import get_engine_alchemy

# --- Initial Setup ---
USER_PY_LOGGING_PREFIX = "CRUD_"

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


engine = get_engine_alchemy()
Session = sessionmaker(bind=engine, expire_on_commit=False)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database transaction failed: {e.orig}", extra={'action': 'SESSION_ROLLBACK'})
        session.rollback()
        raise
    finally:
        session.close()

def add_player(display_name:str) -> Player | None:
    logger.info(f"Attempting to add new player '{display_name}'.", extra={'action': 'ADD_PLAYER_ATTEMPT'})
    try:
        with session_scope() as session:
            new_player = Player(display_name=display_name)
            session.add(new_player)
            session.flush() # Assigns the default values like player_id from the DB
            logger.info(f"Successfully added player '{new_player.display_name}' with ID '{new_player.player_id}'.",
                         extra={'action': 'ADD_PLAYER_SUCCESS', 'entity_id': new_player.player_id})
            return new_player
    except SQLAlchemyError:
        # The error is already logged by session_scope, so we just return None.
        return None
    
def get_player_by_id(player_id:str) -> Player | None:
    """
    Retrieves a player from the database by their unique player_id.

    Args:
        player_id: The UUID of the player to retrieve.

    Returns:
        The Player object if found, otherwise None.
    """
    logger.debug(f"Querying for player with ID '{player_id}'.", extra={'action': 'GET_PLAYER_BY_ID'})
    try:
        with session_scope() as session:
            player = session.query(Player).filter_by(player_id=player_id).first()
            if player:
                logger.debug(f"Found player '{player.display_name}'.", extra={'entity_id': player_id})
            return player
    except SQLAlchemyError:
        return None
    
def update_player_display_name(player_id: str, new_display_name: str, changed_by: str = "SYSTEM") -> bool:
    """
    Updates a player's display name and records the change in the history table.

    Args:
        player_id: The UUID of the player to update.
        new_display_name: The new display name for the player.
        changed_by: Identifier for who made the change (e.g., a Discord User ID).

    Returns:
        True if the name was updated, False otherwise (e.g., player not found or name is the same).
    """
    logger.info(f"Attempting to update name for player '{player_id}' to '{new_display_name}'.",
                extra={'action': 'UPDATE_PLAYER_NAME_ATTEMPT', 'entity_id': player_id})

    try:
        with session_scope() as session:
            player = session.query(Player).filter_by(player_id=player_id).first()

            if not player:
                logger.warning(f"Player with ID '{player_id}' not found for name update.",
                               extra={'action': 'UPDATE_PLAYER_NAME_NOT_FOUND', 'entity_id': player_id})
                return False

            old_display_name = player.display_name
            if old_display_name == new_display_name:
                logger.info(f"Player '{player_id}' name is already '{new_display_name}'. No update needed.",
                            extra={'action': 'UPDATE_PLAYER_NAME_NO_CHANGE', 'entity_id': player_id})
                return False

            # Update the player's current name
            player.display_name = new_display_name

            # Create a history record of the change
            history_entry = PlayerDisplayNameHistory(
                player_id=player_id,
                old_display_name=old_display_name,
                new_display_name=new_display_name,
                changed_by=changed_by
            )
            session.add(history_entry)

            logger.info(f"Updated player '{player_id}' name from '{old_display_name}' to '{new_display_name}'.",
                        extra={'action': 'UPDATE_PLAYER_NAME_SUCCESS', 'entity_id': player_id,
                               'old_value': old_display_name, 'new_value': new_display_name})
            return True
    except SQLAlchemyError:
        return False
    
# --- Riot Account Functions ---

def add_or_update_riot_account(puuid: str, game_name: str, tag_line: str, region: str) -> RiotAccount | None:
    """
    Adds a new Riot account or updates an existing one based on the PUUID.
    If the name or tag line has changed, a history record is created.

    Args:
        puuid: The Riot account's unique PUUID.
        game_name: The current game name.
        tag_line: The current tag line.
        region: The account's region (e.g., 'EUW1').

    Returns:
        The created or updated RiotAccount object, or None on error.
    """
    action_details = {'puuid': puuid, 'game_name': game_name, 'tag_line': tag_line}
    logger.info(f"Attempting to add/update Riot account for PUUID '{puuid}'.",
                extra={'action': 'ADD_UPDATE_RIOT_ACCOUNT_ATTEMPT', **action_details})

    try:
        with session_scope() as session:
            # Check if the account already exists
            account = session.query(RiotAccount).filter_by(puuid=puuid).first()

            if not account:
                # --- Create New Account ---
                new_account = RiotAccount(
                    puuid=puuid,
                    game_name=game_name,
                    tag_line=tag_line,
                    region=region
                )
                session.add(new_account)
                session.flush() # Ensure riot_account_id is available
                logger.info(f"Created new Riot account for '{game_name}#{tag_line}'.",
                            extra={'action': 'ADD_RIOT_ACCOUNT_SUCCESS', 'entity_id': new_account.riot_account_id, **action_details})
                return new_account
            else:
                # --- Update Existing Account ---
                if account.game_name == game_name and account.tag_line == tag_line:
                    logger.debug(f"Riot account for '{puuid}' is already up to date.",
                                 extra={'action': 'UPDATE_RIOT_ACCOUNT_NO_CHANGE', 'entity_id': account.riot_account_id})
                    return account

                old_name = f"{account.game_name}#{account.tag_line}"
                new_name = f"{game_name}#{tag_line}"

                # Create history entry before changing the data
                history_entry = RiotAccountNameHistory(
                    riot_account_id=account.riot_account_id,
                    puuid=puuid,
                    old_game_name=account.game_name,
                    new_game_name=game_name,
                    old_tag_line=account.tag_line,
                    new_tag_line=tag_line,
                    changed_by="SYSTEM_API_UPDATE" # Or another identifier
                )
                session.add(history_entry)

                # Update the account object
                account.game_name = game_name
                account.tag_line = tag_line

                logger.info(f"Updated Riot account name from '{old_name}' to '{new_name}'.",
                            extra={'action': 'UPDATE_RIOT_ACCOUNT_SUCCESS', 'entity_id': account.riot_account_id,
                                   'old_value': old_name, 'new_value': new_name})
                return account

    except SQLAlchemyError:
        return None


def get_riot_account_by_puuid(puuid: str) -> RiotAccount | None:
    """
    Retrieves a Riot account from the database by its unique PUUID.

    Args:
        puuid: The PUUID of the account to retrieve.

    Returns:
        The RiotAccount object if found, otherwise None.
    """
    logger.debug(f"Querying for Riot account with PUUID '{puuid}'.", extra={'action': 'GET_RIOT_BY_PUUID'})
    try:
        with session_scope() as session:
            account = session.query(RiotAccount).filter_by(puuid=puuid).first()
            if account:
                logger.debug(f"Found Riot account '{account.game_name}#{account.tag_line}'.", extra={'entity_id': account.riot_account_id})
            return account
    except SQLAlchemyError:
        return None
    
def link_player_to_riot_account(player_id: str, riot_account_id: str, is_primary: bool = False) -> PlayerRiotAccountLink | None:
    """
    Links a Player to a RiotAccount. It first checks if an ACTIVE link
    already exists. If not, it creates a new link record.

    Args:
        player_id: The UUID of the player.
        riot_account_id: The UUID of the Riot account.
        is_primary: Flag to mark this as the player's primary Riot account.

    Returns:
        The PlayerRiotAccountLink object if the link was created or already existed, otherwise None.
    """
    action_details = {'player_id': player_id, 'riot_account_id': riot_account_id}
    logger.info(f"Attempting to link player to Riot account.",
                extra={'action': 'LINK_PLAYER_RIOT_ATTEMPT', **action_details})

    try:
        with session_scope() as session:
            # Check if the link already exists to avoid violating the unique constraint
            active_link = session.query(PlayerRiotAccountLink).filter_by(
                player_id=player_id,
                riot_account_id=riot_account_id,
                is_active=True
            ).first()

            if active_link:
                logger.debug("Player is already actively linked to this Riot account.",
                             extra={'action': 'LINK_PLAYER_RIOT_ACTIVE_EXISTS', **action_details})
                return active_link

            # Create the new link
            new_link = PlayerRiotAccountLink(
                player_id=player_id,
                riot_account_id=riot_account_id,
                is_primary_riot_account=is_primary
            )
            session.add(new_link)
            session.flush() # To get the link_id
            logger.info("Successfully linked player to Riot account.",
                        extra={'action': 'LINK_PLAYER_RIOT_SUCCESS', 'entity_id': new_link.link_id, **action_details})
            return new_link

    except SQLAlchemyError:
        return None
    
def deactivate_riot_link(player_id: str, riot_account_id: str) -> bool:
    """
    Deactivates the link between a Player and a RiotAccount by setting is_active=False
    and recording the unlinked_at timestamp. This preserves the history.

    Args:
        player_id: The UUID of the player.
        riot_account_id: The UUID of the Riot account.

    Returns:
        True if the link was successfully deactivated, False otherwise.
    """
    action_details = {'player_id': player_id, 'riot_account_id': riot_account_id}
    logger.info(f"Attempting to deactivate link between player and Riot account.",
                extra={'action': 'DEACTIVATE_RIOT_LINK_ATTEMPT', **action_details})
    try:
        with session_scope() as session:
            link_to_update = session.query(PlayerRiotAccountLink).filter_by(
                player_id=player_id,
                riot_account_id=riot_account_id,
                is_active=True  # Only find the currently active link
            ).first()

            if not link_to_update:
                logger.warning("Active link to deactivate was not found.",
                               extra={'action': 'DEACTIVATE_RIOT_LINK_NOT_FOUND', **action_details})
                return False

            # Update the link instead of deleting it
            link_to_update.is_active = False
            link_to_update.unlinked_at = func.now() # from sqlalchemy.sql

            logger.info("Successfully deactivated link between player and Riot account.",
                        extra={'action': 'DEACTIVATE_RIOT_LINK_SUCCESS', **action_details})
            return True

    except SQLAlchemyError:
        return False
    
# --- Discord Account Functions ---

def add_or_update_discord_account(discord_user_id: str, username: str, discriminator: str | None = None) -> DiscordAccount | None:
    """
    Adds a new Discord account or updates an existing one based on the discord_user_id.

    Args:
        discord_user_id: The unique Discord User ID.
        username: The current Discord username.
        discriminator: The 4-digit discriminator (for older usernames, can be None).

    Returns:
        The created or updated DiscordAccount object, or None on error.
    """
    action_details = {'discord_user_id': discord_user_id, 'username': username}
    logger.info(f"Attempting to add/update Discord account for user ID '{discord_user_id}'.",
                extra={'action': 'ADD_UPDATE_DISCORD_ACCOUNT_ATTEMPT', **action_details})

    try:
        with session_scope() as session:
            account = session.query(DiscordAccount).filter_by(discord_user_id=discord_user_id).first()

            if not account:
                # --- Create New Account ---
                new_account = DiscordAccount(
                    discord_user_id=discord_user_id,
                    discord_username=username,
                    discriminator=discriminator
                )
                session.add(new_account)
                session.flush()
                logger.info(f"Created new Discord account for '{username}'.",
                            extra={'action': 'ADD_DISCORD_ACCOUNT_SUCCESS', 'entity_id': new_account.discord_account_id, **action_details})
                return new_account
            else:
                # --- Update Existing Account ---
                if account.discord_username == username and account.discriminator == discriminator:
                    logger.debug(f"Discord account for '{discord_user_id}' is already up to date.",
                                 extra={'action': 'UPDATE_DISCORD_ACCOUNT_NO_CHANGE', 'entity_id': account.discord_account_id})
                    return account

                account.discord_username = username
                account.discriminator = discriminator
                logger.info(f"Updated Discord account for user ID '{discord_user_id}'.",
                            extra={'action': 'UPDATE_DISCORD_ACCOUNT_SUCCESS', 'entity_id': account.discord_account_id, **action_details})
                return account

    except SQLAlchemyError:
        return None
    
def link_player_to_discord_account(player_id: str, discord_account_id: str, is_primary: bool = False) -> PlayerDiscordAccountLink | None:
    """
    Links a Player to a DiscordAccount. It first checks if an ACTIVE link
    already exists. If not, it creates a new link record.

    Args:
        player_id: The UUID of the player.
        discord_account_id: The UUID of the Discord account.
        is_primary: Flag to mark this as the player's primary Discord account.

    Returns:
        The PlayerDiscordAccountLink object if the link was created or already existed, otherwise None.
    """
    action_details = {'player_id': player_id, 'discord_account_id': discord_account_id}
    logger.info(f"Attempting to link player to Discord account.",
                extra={'action': 'LINK_PLAYER_DISCORD_ATTEMPT', **action_details})

    try:
        with session_scope() as session:
            # Check only for an ACTIVE link
            active_link = session.query(PlayerDiscordAccountLink).filter_by(
                player_id=player_id,
                discord_account_id=discord_account_id,
                is_active=True
            ).first()

            if active_link:
                logger.debug("Player is already actively linked to this Discord account.",
                             extra={'action': 'LINK_PLAYER_DISCORD_ACTIVE_EXISTS', **action_details})
                return active_link

            # Create a new link record
            new_link = PlayerDiscordAccountLink(
                player_id=player_id,
                discord_account_id=discord_account_id,
                is_primary_account=is_primary
            )
            session.add(new_link)
            session.flush()
            logger.info("Successfully created new link for player to Discord account.",
                        extra={'action': 'LINK_PLAYER_DISCORD_SUCCESS', 'entity_id': new_link.link_id, **action_details})
            return new_link

    except SQLAlchemyError:
        return None
    
def deactivate_discord_link(player_id: str, discord_account_id: str) -> bool:
    """
    Deactivates the link between a Player and a DiscordAccount by setting is_active=False
    and recording the unlinked_at timestamp.

    Args:
        player_id: The UUID of the player.
        discord_account_id: The UUID of the Discord account.

    Returns:
        True if the link was successfully deactivated, False otherwise.
    """
    action_details = {'player_id': player_id, 'discord_account_id': discord_account_id}
    logger.info(f"Attempting to deactivate link between player and Discord account.",
                extra={'action': 'DEACTIVATE_DISCORD_LINK_ATTEMPT', **action_details})
    try:
        with session_scope() as session:
            link_to_update = session.query(PlayerDiscordAccountLink).filter_by(
                player_id=player_id,
                discord_account_id=discord_account_id,
                is_active=True  # Only find the currently active link
            ).first()

            if not link_to_update:
                logger.warning("Active link to deactivate was not found.",
                               extra={'action': 'DEACTIVATE_DISCORD_LINK_NOT_FOUND', **action_details})
                return False

            # Update the link instead of deleting it
            link_to_update.is_active = False
            link_to_update.unlinked_at = func.now()

            logger.info("Successfully deactivated link between player and Discord account.",
                        extra={'action': 'DEACTIVATE_DISCORD_LINK_SUCCESS', **action_details})
            return True

    except SQLAlchemyError:
        return False

# --- Server and Race Functions ---

def add_or_update_server(server_id: str, server_name: str, owner_id: str | None = None) -> DiscordServer | None:
    """
    Adds a new Discord server to the database or updates its name if it already exists.

    Args:
        server_id: The unique Discord Guild ID.
        server_name: The current name of the server.
        owner_id: The Discord User ID of the server's owner.

    Returns:
        The created or updated DiscordServer object, or None on error.
    """
    action_details = {'server_id': server_id, 'server_name': server_name}
    logger.info(f"Attempting to add/update server '{server_name}'.",
                extra={'action': 'ADD_UPDATE_SERVER_ATTEMPT', **action_details})
    try:
        with session_scope() as session:
            server = session.query(DiscordServer).filter_by(server_id=server_id).first()

            if not server:
                new_server = DiscordServer(
                    server_id=server_id,
                    server_name=server_name,
                    owner_discord_user_id=owner_id
                )
                session.add(new_server)
                logger.info("Added new server to the database.",
                            extra={'action': 'ADD_SERVER_SUCCESS', **action_details})
                return new_server
            else:
                if server.server_name != server_name:
                    server.server_name = server_name
                    logger.info("Updated server name.",
                                extra={'action': 'UPDATE_SERVER_SUCCESS', **action_details})
                return server
    except SQLAlchemyError:
        return None


def add_player_to_server(player_id: str, server_id: str) -> ServerPlayer | None:
    """
    Links a player to a specific server, creating a ServerPlayer record.

    Args:
        player_id: The UUID of the player.
        server_id: The ID of the server.

    Returns:
        The ServerPlayer object if the link was created or already existed, otherwise None.
    """
    action_details = {'player_id': player_id, 'server_id': server_id}
    logger.info(f"Attempting to add player to server.",
                extra={'action': 'ADD_PLAYER_TO_SERVER_ATTEMPT', **action_details})
    try:
        with session_scope() as session:
            # Check if the player is already on the server
            existing_server_player = session.query(ServerPlayer).filter_by(
                player_id=player_id,
                server_id=server_id
            ).first()

            if existing_server_player:
                # If the player was marked as inactive, reactivate them.
                if not existing_server_player.is_active_on_server:
                    existing_server_player.is_active_on_server = True
                    logger.info("Reactivated player on server.",
                                extra={'action': 'REACTIVATE_SERVER_PLAYER_SUCCESS', **action_details})
                else:
                    logger.debug("Player is already active on this server.",
                                 extra={'action': 'ADD_PLAYER_TO_SERVER_EXISTS', **action_details})
                return existing_server_player

            new_server_player = ServerPlayer(
                player_id=player_id,
                server_id=server_id
            )
            session.add(new_server_player)
            session.flush()
            logger.info("Successfully added player to server.",
                        extra={'action': 'ADD_PLAYER_TO_SERVER_SUCCESS',
                               'entity_id': new_server_player.server_player_id, **action_details})
            return new_server_player
    except SQLAlchemyError:
        return None
    
def create_race(server_id: str, name: str, start_time: datetime, end_time: datetime, **kwargs) -> Race | None:
    """
    Creates a new race for a specific server.

    Args:
        server_id: The ID of the server hosting the race.
        name: The name of the race.
        start_time: The starting timestamp of the race.
        end_time: The ending timestamp of the race.
        **kwargs: Optional arguments for other Race fields like:
                  description (str), status (str), race_type (str),
                  target_value (int), created_by_discord_user_id (str).

    Returns:
        The newly created Race object, or None on error.
    """
    action_details = {'server_id': server_id, 'race_name': name}
    logger.info(f"Attempting to create new race '{name}'.",
                extra={'action': 'CREATE_RACE_ATTEMPT', **action_details})

    try:
        with session_scope() as session:
            new_race = Race(
                server_id=server_id,
                race_name=name,
                start_time=start_time,
                end_time=end_time,
                # --- Populate optional fields from kwargs ---
                description=kwargs.get('description'),
                status=kwargs.get('status', 'planned'),
                race_type=kwargs.get('race_type'),
                target_value=kwargs.get('target_value'),
                created_by_discord_user_id=kwargs.get('created_by_discord_user_id')
            )
            session.add(new_race)
            session.flush()
            logger.info("Successfully created new race.",
                        extra={'action': 'CREATE_RACE_SUCCESS', 'entity_id': new_race.race_id, **action_details})
            return new_race

    except SQLAlchemyError:
        return None
    
def add_participant_to_race(race_id: str, server_player_id: str, **kwargs) -> RaceParticipant | None:
    """
    Adds a player (via their ServerPlayer ID) as a participant in a race.

    Args:
        race_id: The UUID of the race.
        server_player_id: The UUID of the ServerPlayer record.
        **kwargs: Optional arguments for other RaceParticipant fields, like:
                  starting_value (int).

    Returns:
        The RaceParticipant object if created or already existing, otherwise None.
    """
    action_details = {'race_id': race_id, 'server_player_id': server_player_id}
    logger.info(f"Attempting to add participant to race.",
                extra={'action': 'ADD_PARTICIPANT_ATTEMPT', **action_details})
    try:
        with session_scope() as session:
            # Check if this player is already in the race
            existing_participant = session.query(RaceParticipant).filter_by(
                race_id=race_id,
                server_player_id=server_player_id
            ).first()

            if existing_participant:
                logger.debug("Player is already a participant in this race.",
                             extra={'action': 'ADD_PARTICIPANT_EXISTS', **action_details})
                return existing_participant

            new_participant = RaceParticipant(
                race_id=race_id,
                server_player_id=server_player_id,
                # --- Populate optional fields from kwargs ---
                starting_value=kwargs.get('starting_value')
            )
            session.add(new_participant)
            session.flush()
            logger.info("Successfully added new participant to race.",
                        extra={'action': 'ADD_PARTICIPANT_SUCCESS',
                               'entity_id': new_participant.participant_id, **action_details})
            return new_participant

    except SQLAlchemyError:
        return None