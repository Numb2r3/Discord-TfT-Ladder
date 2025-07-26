from dotenv import dotenv_values
import sqlalchemy
from sqlalchemy import text
import os
import mysql.connector 
import psycopg2
import pandas as pd

def get_sql_config():
    '''
        Function loads credentials from .env file and
        returns a dictionary containing the data needed for sqlalchemy.create_engine()
    '''
    needed_keys = ['host', 'port', 'dbname','user','password','db_type']
    dotenv_dict = dotenv_values(".env")
    sql_config = {key:dotenv_dict.get(key) for key in needed_keys}
    return sql_config

# Insert the get_engine() function definition below - when instructed
def get_engine_alchemy():
        sql_config = get_sql_config()
        db_type = sql_config.get('db_type', 'postgresql') # Standard auf postgresql
        host = sql_config.get('host')
        port = sql_config.get('port')
        dbname = sql_config.get('dbname')
        user = sql_config.get('user')
        password = sql_config.get('password')

        if db_type == 'postgresql':
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        elif db_type == 'mysql':
            db_url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{dbname}"
        elif db_type == 'sqlite': # Füge SQLite Unterstützung hinzu
            db_file = os.getenv('SQLITE_DB_FILE', 'tft_players.db') # Holen aus .env oder Standard
            db_url = f"sqlite:///{db_file}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        engine = sqlalchemy.create_engine(db_url)
        return engine

# Insert the get_data() function definition below - do this only when instructed in the notebook
def get_data_alchemy(query):
    engine = get_engine_alchemy()
    query = text(query)
    with engine.begin() as conn:
        results = conn.execute(query)
        return results.fetchall()
    

# Insert the get_dataframe() function definition below - do this only when instructed in the notebook
def get_dataframe(query,engine):
    engine = engine
    
    return pd.read_sql_query(sql=query, con = engine)


def push_to_database(df, table_name, engine, schema):
    if engine!=None:
        try:
            df.to_sql(name=table_name, # Name of SQL table
                            con=engine, # Engine or connection
                            if_exists='append', # Drop the table before inserting new values
                            schema=schema, # Use schema that was defined earlier
                            index=False, # Write DataFrame index as a column
                            chunksize=5000, # Specify the number of rows in each batch to be written at a time
                            method='multi') # Pass multiple values in a single INSERT clause
            print(f"The {table_name} table was imported successfully.")
        # Error handling
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            engine = None

def send(query):
    engine = get_engine_alchemy()
    query = text(query)                 #since sqlalchemy2.0 text is necessary

    with engine.connect() as con:
        con.execute(query)
    #cursor = engine.cursor()
    #cursor.execute(query)
    #engine.commit()
    #cursor.close()
    #engine.close()
    return



def get_engine_mysql():
    engine = mysql.connector.connect(**get_sql_config())
    return engine


def get_data_mysql(query):
    engine = get_engine_mysql()

    cursor = engine.cursor()
    cursor.execute(query)
    results = []
    for i, data in enumerate(cursor):
        results.append(data)
    cursor.close()
    engine.close()
    return results