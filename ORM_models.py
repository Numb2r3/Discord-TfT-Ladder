from sqlalchemy import Column, String, DateTime,Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import create_engine # Für die Engine-Erstellung, falls hier nicht getrennt
from sqlalchemy.sql import func
import uuid 

Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(String(36),primary_key=True,default=lambda: str(uuid.uuid4()))

    display_name = Column(String(255),nullable=False)

    
    added_at = Column(DateTime,default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Player(player_id='{self.player_id}', display_name='{self.display_name}')>"

class PlayerDisplayNameHistory(Base):
    __tablename__ = 'player_display_name_history'

    history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key zur Player-Tabelle
    player_id = Column(String(36), ForeignKey('players.player_id'), nullable=False)

    old_display_name = Column(String(255), nullable=False)
    new_display_name = Column(String(255), nullable=False)

    # Zeitstempel der Änderung
    changed_at = Column(DateTime, default=func.now(), nullable=False)

    # Optional: Wer die Änderung vorgenommen hat (z.B. Discord User ID)
    changed_by = Column(String(255), nullable=True) # Kann NULL sein, wenn z.B. vom System geändert

    # Relationship zur Player-Tabelle
    player = relationship("Player", backref="display_name_history")
    # backref erstellt automatisch ein 'display_name_history' Attribut auf dem Player-Objekt

    def __repr__(self):
        return f"<PlayerDisplayNameHistory(player_id='{self.player_id}', old_name='{self.old_display_name}', new_name='{self.new_display_name}')>"
    

class DiscordAccount(Base):
    __tablename__ = 'discord_accounts'

    # discord_account_id: Eindeutige interne ID für jeden Discord-Account (unsere eigene UUID)
    discord_account_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # discord_user_id: Die numerische Discord User ID (die stabile ID von Discord)
    # Diese sollte von Discord eindeutig sein, daher UNIQUE
    discord_user_id = Column(String(255), unique=True, nullable=False)

    # discord_username: Der aktuelle Discord-Benutzername (z.B. "exampleuser#1234")
    # Kann sich ändern, daher keine UNIQUE-Eigenschaft hier. Historie wird später überlegt.
    discord_username = Column(String(255), nullable=False)

    # discriminator (Optional): Der 4-stellige Tag (für alte Discord-Namen, vor dem Username-Update)
    discriminator = Column(String(4), nullable=True)


    # created_at: Zeitpunkt der Erstellung des Eintrags in deiner DB
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # last_updated: Zeitpunkt der letzten Aktualisierung der Account-Details (z.B. Name, Avatar)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships (werden später hinzugefügt, wenn PlayerDiscordAccountLink definiert ist)
    # linked_players = relationship("PlayerDiscordAccountLink", back_populates="discord_account")

    def __repr__(self):
        return f"<DiscordAccount(discord_user_id='{self.discord_user_id}', username='{self.discord_username}')>"


class PlayerDiscordAccountLink(Base):
    __tablename__ = 'player_discord_account_links'

    # link_id: Eindeutige ID für diese spezifische Verknüpfung
    link_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # player_id (Foreign Key): Verweist auf Players.player_id
    player_id = Column(String(36), ForeignKey('players.player_id'), nullable=False)

    # discord_account_id (Foreign Key): Verweist auf DiscordAccounts.discord_account_id
    discord_account_id = Column(String(36), ForeignKey('discord_accounts.discord_account_id'), nullable=False)

    # Zusätzlicher UNIQUE-Constraint, um doppelte Verknüpfungen zu verhindern
    # Ein Paar aus player_id und discord_account_id darf nur einmal vorkommen.
    __table_args__ = (
        UniqueConstraint('player_id', 'discord_account_id', name='_player_discord_uc'),
    )

    # is_primary_account (Optional): Flag, ob dies der primäre Discord-Account für diesen Spieler ist
    is_primary_account = Column(Boolean, default=False, nullable=False)

    # linked_at: Zeitpunkt der Verknüpfung
    linked_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships:
    # Direkte Beziehung zu den verknüpften Modellen
    player = relationship("Player", backref="discord_account_links")
    discord_account = relationship("DiscordAccount", backref="player_links")

    def __repr__(self):
        return f"<PlayerDiscordAccountLink(player_id='{self.player_id}', discord_account_id='{self.discord_account_id}', is_primary={self.is_primary_account})>"
    

class RiotAccount(Base):
    __tablename__ = 'riot_accounts'

    # riot_account_id (Primary Key): Eindeutige interne ID für jeden Riot Account.
    riot_account_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # puuid (Unique): Die Persistent Unique ID von Riot (die stabile ID, auch bei Namensänderungen).
    # Dies ist der wichtigste externe Identifikator von Riot.
    puuid = Column(String(78), unique=True, nullable=False) # PUUIDs sind 78 Zeichen lang

    # game_name: Der aktuelle Ingame-Name (Riot ID).
    game_name = Column(String(255), nullable=False)

    # tag_line: Der Tag der Riot ID (z.B. #EUW), notwendig für API-Abfragen.
    tag_line = Column(String(10), nullable=False) # Taglines sind kurz, z.B. #EUW, #NA1

    # region: Die Spielregion des Accounts (z.B. "EUW", "NA").
    region = Column(String(10), nullable=False) # Kurzform der Region

    # created_at: Zeitpunkt der Erstellung des Eintrags in deiner DB.
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # last_api_update (Optional): Letzter Zeitpunkt der Datenaktualisierung über die Riot API.
    # Wichtig, um zu wissen, wann die Daten das letzte Mal von Riot geholt wurden.
    last_api_update = Column(DateTime, nullable=True) # Standardmäßig NULL

    # Relationships (werden später hinzugefügt, wenn PlayerRiotAccountLink definiert ist)
    # linked_players = relationship("PlayerRiotAccountLink", back_populates="riot_account")
    # name_history = relationship("RiotAccountNameHistory", back_populates="riot_account")


    def __repr__(self):
        return f"<RiotAccount(puuid='{self.puuid}', name='{self.game_name}#{self.tag_line}', region='{self.region}')>"


class RiotAccountNameHistory(Base):
    __tablename__ = 'riot_account_name_history'

    # history_id: Eindeutige ID für jeden Eintrag in dieser Historie-Tabelle
    history_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # riot_account_id (Foreign Key): Verweist auf RiotAccounts.riot_account_id
    riot_account_id = Column(String(36), ForeignKey('riot_accounts.riot_account_id'), nullable=False)

    # puuid: Die PUUID des Accounts zum Zeitpunkt der Änderung (kann zur schnelleren Abfrage redundant sein)
    # Nicht als FK, da die FK-Beziehung über riot_account_id läuft. Aber nützlich für direkte Abfragen.
    puuid = Column(String(78), nullable=False)

    # old_game_name: Der vorherige game_name
    old_game_name = Column(String(255), nullable=False)
    # new_game_name: Der neue game_name
    new_game_name = Column(String(255), nullable=False)

    # old_tag_line: Die vorherige tag_line
    old_tag_line = Column(String(10), nullable=False)
    # new_tag_line: Die neue tag_line
    new_tag_line = Column(String(10), nullable=False)

    # changed_at: Zeitstempel, wann die Namensänderung stattfand
    changed_at = Column(DateTime, default=func.now(), nullable=False)

    # changed_by (Optional): Die Discord User ID des Benutzers, der die Änderung ausgelöst hat (oder 'SYSTEM')
    changed_by = Column(String(255), nullable=True)

    # Relationships:
    # Beziehung zur RiotAccount-Tabelle
    riot_account = relationship("RiotAccount", backref="name_history")

    def __repr__(self):
        return (f"<RiotAccountNameHistory(riot_account_id='{self.riot_account_id}', "
                f"old_name='{self.old_game_name}#{self.old_tag_line}', "
                f"new_name='{self.new_game_name}#{self.new_tag_line}', "
                f"changed_at='{self.changed_at}')>")
    

# In ORM_models.py, unter der RiotAccountNameHistory-Klasse

class PlayerRiotAccountLink(Base):
    __tablename__ = 'player_riot_account_links'

    # link_id: Eindeutige ID für diese spezifische Verknüpfung
    link_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # player_id (Foreign Key): Verweist auf Players.player_id
    player_id = Column(String(36), ForeignKey('players.player_id'), nullable=False)

    # riot_account_id (Foreign Key): Verweist auf RiotAccounts.riot_account_id
    riot_account_id = Column(String(36), ForeignKey('riot_accounts.riot_account_id'), nullable=False)

    # Zusätzlicher UNIQUE-Constraint, um doppelte Verknüpfungen zu verhindern
    # Ein Paar aus player_id und riot_account_id darf nur einmal vorkommen.
    __table_args__ = (
        UniqueConstraint('player_id', 'riot_account_id', name='_player_riot_uc'),
    )

    # is_primary_riot_account (Optional): Flag, ob dies der primäre Riot-Account für diesen Spieler ist
    is_primary_riot_account = Column(Boolean, default=False, nullable=False)

    # linked_at: Zeitpunkt der Verknüpfung
    linked_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships:
    # Direkte Beziehung zu den verknüpften Modellen
    player = relationship("Player", backref="riot_account_links")
    riot_account = relationship("RiotAccount", backref="player_links")

    def __repr__(self):
        return (f"<PlayerRiotAccountLink(player_id='{self.player_id}', "
                f"riot_account_id='{self.riot_account_id}', "
                f"is_primary_riot_account={self.is_primary_riot_account})>")
    

class DiscordServer(Base):
    __tablename__ = 'discord_servers'

    # server_id (Primary Key): Die Discord Guild ID (die eindeutige ID des Servers von Discord).
    # Diese ID ist extern und von Discord vergeben, und sollte der Primärschlüssel sein.
    server_id = Column(String(255), primary_key=True, nullable=False) # Discord Guild IDs sind Strings

    # server_name: Der aktuelle Name des Discord-Servers.
    # Kann sich ändern.
    server_name = Column(String(255), nullable=False)

    # owner_discord_user_id (Optional): Die Discord User ID des Serverbesitzers.
    # Kann nützlich sein für spezielle Berechtigungen oder Kontaktaufnahme.
    owner_discord_user_id = Column(String(255), nullable=True)

    # added_at: Zeitpunkt, wann der Server in die DB aufgenommen wurde (d.h. wann der Bot beitrat).
    added_at = Column(DateTime, default=func.now(), nullable=False)

    # last_active (Optional): Letzter Zeitpunkt der Bot-Aktivität auf diesem Server.
    # Nützlich, um inaktive Server zu identifizieren.
    last_active = Column(DateTime, nullable=True) # Default NULL, wird bei Aktivität aktualisiert

    # Relationships (werden später hinzugefügt, wenn ServerPlayers und Races definiert sind)
    # server_players = relationship("ServerPlayer", back_populates="discord_server")
    # races = relationship("Race", back_populates="discord_server")

    def __repr__(self):
        return f"<DiscordServer(server_id='{self.server_id}', name='{self.server_name}')>"
    
# In ORM_models.py, unter der DiscordServer-Klasse

class ServerPlayer(Base):
    __tablename__ = 'server_players'

    # server_player_id (Primary Key): Eindeutige ID für diese server-spezifische Spieler-Verbindung.
    server_player_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # server_id (Foreign Key): Verweist auf DiscordServers.server_id.
    # Verbindet diesen Eintrag mit dem spezifischen Discord-Server.
    server_id = Column(String(255), ForeignKey('discord_servers.server_id'), nullable=False)

    # player_id (Foreign Key): Verweist auf Players.player_id.
    # Verbindet diesen Eintrag mit dem logischen Spieler.
    player_id = Column(String(36), ForeignKey('players.player_id'), nullable=False)

    # Zusätzlicher UNIQUE-Constraint, um doppelte Verknüpfungen zu verhindern
    # Ein Paar aus server_id und player_id darf nur einmal vorkommen.
    __table_args__ = (
        UniqueConstraint('server_id', 'player_id', name='_server_player_uc'),
    )

    # joined_server_at: Zeitpunkt, wann der Spieler auf diesem Server in deinem System hinzugefügt wurde.
    # Dies ist der Zeitpunkt, ab dem der Bot diesen Spieler auf diesem Server 'kennt'.
    joined_server_at = Column(DateTime, default=func.now(), nullable=False)

    # is_active_on_server: Flag, ob der Spieler auf diesem Server aktiv ist oder getrackt werden soll.
    # Nützlich, um Spieler zu deaktivieren, die den Server verlassen haben oder nicht mehr getrackt werden sollen.
    is_active_on_server = Column(Boolean, default=True, nullable=False) # Standardmäßig aktiv

    # Relationships:
    # Direkte Beziehung zu den verknüpften Modellen
    discord_server = relationship("DiscordServer", backref="server_players")
    player = relationship("Player", backref="server_links")

    def __repr__(self):
        return (f"<ServerPlayer(server_player_id='{self.server_player_id}', "
                f"server_id='{self.server_id}', player_id='{self.player_id}', "
                f"is_active={self.is_active_on_server})>")
    


class Race(Base):
    __tablename__ = 'races'

    # race_id (Primary Key): Eindeutige ID für die Race.
    race_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # server_id (Foreign Key): Verweist auf DiscordServers.server_id.
    # Verbindet die Race mit dem spezifischen Server, auf dem sie stattfindet.
    server_id = Column(String(255), ForeignKey('discord_servers.server_id'), nullable=False)

    # race_name: Der Name der Race.
    race_name = Column(String(255), nullable=False)

    # description (Optional): Eine Beschreibung der Race.
    description = Column(String(1024), nullable=True) # Längerer String für Beschreibungen

    # start_time: Startzeitpunkt der Race.
    start_time = Column(DateTime, nullable=False)

    # end_time: Endzeitpunkt der Race.
    end_time = Column(DateTime, nullable=False)

    # status: Aktueller Status der Race (z.B. "planned", "active", "finished", "cancelled").
    # Ein String, der den Status repräsentiert.
    status = Column(String(50), nullable=False, default="planned")

    # race_type (Optional): Art der Race (z.B. "LP Climb", "Top 4 Count", "Placement Average").
    race_type = Column(String(100), nullable=True)

    # target_value (Optional): Ein numerisches Ziel der Race (z.B. Ziel-LP, Ziel-Top-4-Anzahl).
    target_value = Column(Integer, nullable=True) # Oder Float, je nach dem, was getrackt wird

    # created_at: Zeitpunkt der Erstellung des Race-Eintrags in deiner DB.
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # created_by_discord_user_id (Optional): Discord User ID des Erstellers der Race.
    created_by_discord_user_id = Column(String(255), nullable=True)

    # Relationships:
    # Beziehung zum DiscordServer
    discord_server = relationship("DiscordServer", backref="races")
    # Teilnehmer an dieser Race (wird mit RaceParticipant verknüpft)
    # participants = relationship("RaceParticipant", back_populates="race")


    def __repr__(self):
        return (f"<Race(race_id='{self.race_id}', server_id='{self.server_id}', "
                f"name='{self.race_name}', status='{self.status}', "
                f"start='{self.start_time.strftime('%Y-%m-%d %H:%M')}')>")
    
# In ORM_models.py, unter der Race-Klasse

class RaceParticipant(Base):
    __tablename__ = 'race_participants'

    # participant_id (Primary Key): Eindeutige ID für die Race-Teilnahme.
    participant_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # race_id (Foreign Key): Verweist auf Races.race_id.
    # Verbindet diesen Teilnehmer mit der spezifischen Race.
    race_id = Column(String(36), ForeignKey('races.race_id'), nullable=False)

    # server_player_id (Foreign Key): Verweist auf ServerPlayers.server_player_id.
    # Verbindet den spezifischen Spieler auf dem spezifischen Server mit der Race.
    server_player_id = Column(String(36), ForeignKey('server_players.server_player_id'), nullable=False)

    # Zusätzlicher UNIQUE-Constraint, um doppelte Teilnahmen zu verhindern
    # Ein Paar aus race_id und server_player_id darf nur einmal vorkommen.
    __table_args__ = (
        UniqueConstraint('race_id', 'server_player_id', name='_race_participant_uc'),
    )

    # starting_value (Optional): Startwert des Teilnehmers in der Race (z.B. Start-LP).
    starting_value = Column(Integer, nullable=True) # Oder Float, je nach race_type

    # final_value (Optional): Endwert des Teilnehmers in der Race.
    final_value = Column(Integer, nullable=True) # Oder Float

    # final_rank (Optional): Die Platzierung in der Race.
    final_rank = Column(Integer, nullable=True)

    # is_disqualified (Optional): Flag, ob der Teilnehmer disqualifiziert wurde.
    is_disqualified = Column(Boolean, default=False, nullable=False)

    # joined_race_at: Zeitpunkt des Beitritts zur Race.
    joined_race_at = Column(DateTime, default=func.now(), nullable=False)

    # last_progress_update (Optional): Letzter Zeitpunkt der Fortschrittsaktualisierung.
    # Nützlich, um zu wissen, wann die Daten des Teilnehmers das letzte Mal aktualisiert wurden.
    last_progress_update = Column(DateTime, nullable=True)

    # Relationships:
    # Direkte Beziehung zur Race
    race = relationship("Race", backref="participants")
    # Direkte Beziehung zum ServerPlayer
    server_player = relationship("ServerPlayer", backref="race_participations")

    def __repr__(self):
        return (f"<RaceParticipant(participant_id='{self.participant_id}', "
                f"race_id='{self.race_id}', server_player_id='{self.server_player_id}', "
                f"final_rank={self.final_rank}, disqualified={self.is_disqualified})>")