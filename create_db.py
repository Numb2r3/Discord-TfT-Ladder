from ORM_models import Base # Importiere nur Base, da alle Modelle daran registriert sind
from sql_functions import get_engine_alchemy
import logging
from dotenv import load_dotenv


load_dotenv()

logger = None
USER_PY_LOGGING_PREFIX = "DB_INIT_"

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

def create_database_tables():
    logger.info("Starting database table creation process.", extra={'action': 'DB_CREATE_PROCESS_START'})
    try:
        engine = get_engine_alchemy()
        logger.info("Database engine successfully retrieved.", extra={'action': 'DB_ENGINE_READY'})

        # Erstelle alle in Base.metadata registrierten Tabellen in der Datenbank
        logger.info("Starting SQLAlchemy Base.metadata.create_all() to create tables.", extra={'action': 'DB_TABLE_CREATION_START'})
        Base.metadata.create_all(engine)
        logger.info("Database and all tables created successfully!", extra={'action': 'DB_TABLE_CREATION_SUCCESS'})

        print("Database and tables created successfully!")

    except Exception as e:
        logger.critical(f"FATAL ERROR during database creation: {e}", extra={'action': 'DB_TABLE_CREATION_FAILED'})
        print(f"ERROR: Failed to create database tables. Check logs for details: {e}")

# --- Hauptausführung ---
if __name__ == "__main__":
    create_database_tables()