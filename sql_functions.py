from dotenv import dotenv_values
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import os
import pandas as pd

def get_sql_config():
    '''
        Function loads credentials from .env file and
        returns a dictionary containing the data.
    '''
    needed_keys = ['host', 'port', 'dbname', 'user', 'password', 'db_type']
    dotenv_dict = dotenv_values(".env")
    sql_config = {key: dotenv_dict.get(key) for key in needed_keys}
    return sql_config

def get_engine_and_session_factory():
    """
    Creates the database engine and returns it along with a session factory.
    This is the central point for database connection setup.
    """
    sql_config = get_sql_config()
    db_type = sql_config.get('db_type', 'postgresql')
    host = sql_config.get('host')
    port = sql_config.get('port')
    dbname = sql_config.get('dbname')
    user = sql_config.get('user')
    password = sql_config.get('password')

    if db_type == 'postgresql':
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == 'mysql':
        db_url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == 'sqlite':
        db_file = os.getenv('SQLITE_DB_FILE', 'tft_players.db')
        db_url = f"sqlite:///{db_file}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    engine = sqlalchemy.create_engine(db_url)
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    return engine, SessionFactory