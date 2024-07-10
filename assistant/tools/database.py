import os

from typing import Literal

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import pandas as pd

load_dotenv()

MY_SQL_HOST=os.getenv('MY_SQL_HOST','localhost')
MY_SQL_PORT=os.getenv('MY_SQL_PORT', '80')
MY_SQL_USER= os.getenv('MY_SQL_USER','user')
MY_SQL_PASSWORD=os.getenv('MY_SQL_PASSWORD','mysql')
MY_SQL_DATABASE=os.getenv('MY_SQL_DATABASE','mysql')

POSTGRES_HOST=os.getenv('POSTGRES_HOST','postgres')
POSTGRES_PORT=os.getenv('POSTGRES_PORT', '5432')
POSTGRES_USER= os.getenv('POSTGRES_USER','postgres')
POSTGRES_PASSWORD=os.getenv('POSTGRES_PASSWORD','postgres')
POSTGRES_DATABASE=os.getenv('POSTGRES_DB','postgres')

MY_SQL_CONNECTION_STRING = f'mysql+pymysql://{MY_SQL_USER}:{MY_SQL_PASSWORD}@{MY_SQL_HOST}:{MY_SQL_PORT}/{MY_SQL_DATABASE}'
MY_SQL_ENGINE = create_engine(MY_SQL_CONNECTION_STRING)


POSTGRES_CONNECTION_STRING = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}'
POSTGRES_ENGINE = create_engine(POSTGRES_CONNECTION_STRING)

ENGINE_DICT = {'my_sql': MY_SQL_ENGINE, 'postgres': POSTGRES_ENGINE}
CURRENT_PATH = os.path.dirname(__file__)

def __create_prompt_version_table__():
  with sessionmaker(bind=POSTGRES_ENGINE)() as session:
    try:
      query = '''DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_type') THEN
            CREATE TYPE status_type AS ENUM ('development', 'stage', 'production', 'archived');
        END IF;
      END
      $$;

      CREATE TABLE IF NOT EXISTS prompt_version (
        prompt_id SERIAL PRIMARY KEY,
        prompt_instructions TEXT CHECK (length(prompt_instructions) <= 5000),
        prompt_input TEXT CHECK (length(prompt_input) <= 20000),
        status status_type,
        creation_date DATE NOT NULL,
        to_production_date DATE,
        to_archive_date DATE,
        base_llm_name VARCHAR(30) NOT NULL
      )'''

      session.execute(text(query))
      session.commit()
    except Exception as e:
      session.rollback()
      print(f"An error occurred: {e}")

def __create_model_quality_table__():
  with sessionmaker(bind=POSTGRES_ENGINE)() as session:
    try:
      query = '''DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_type') THEN
            CREATE TYPE source_type AS ENUM ('model', 'user');
        END IF;
      END
      $$;

      CREATE TABLE IF NOT EXISTS model_quality (
        interaction_id SERIAL PRIMARY KEY,
        prompt_id INT REFERENCES prompt_version(prompt_id),
        input_information TEXT NOT NULL,
        output_model TEXT NOT NULL,
        source source_type,
        user_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )'''

      session.execute(text(query))
      session.commit()
    except Exception as e:
      session.rollback()
      print(f"An error occurred: {e}")

def __create_database_schema_documentation__():
  with sessionmaker(bind=POSTGRES_ENGINE)() as session:
    try:
      query = '''DO $$
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_type') THEN
            CREATE TYPE entity_category_type AS ENUM ('table', 'field');
        END IF;
      END
      $$;
      
      CREATE TABLE IF NOT EXISTS schema_documentation (
        entity_id SERIAL PRIMARY KEY,
        entity_name VARCHAR(30) NOT NULL,
        entity_category entity_category_type NOT NULL,
        entity_parent VARCHAR(30),
        entity_description TEXT,
        entity_type as VARCHAR(20)
      )'''

      session.execute(text(query))
      session.commit()
    except Exception as e:
      session.rollback()
      print(f"An error occurred: {e}")

def __format_schema_description__(description_table: pd.DataFrame) -> str:

  schema_description_text = []

  tables_information = description_table.query('entity_category == "table"')
  for table_name in tables_information['entity_name'].values:
    table_fields = description_table.query(f'entity_parent=="{table_name}"')

    [[name, desc]] = description_table\
                          .query(f'entity_name == "{table_name}"')\
                          [['entity_name', 'entity_description']]\
                          .values
    table_descriptions = [f'Table Name: {name}. Table Description: {desc}']
    table_descriptions.append('  Columns:')
    
    for _, row in table_fields[['entity_name', 'entity_type', 'entity_description']].iterrows():
      name, cast, desc = row
      field_description = f'    {name}: {desc}. Data Type: {cast}.'
      table_descriptions.append(field_description)

    schema_description_text.append('\n'.join(table_descriptions))

  return '\n\n'.join(schema_description_text)

def initialize():
  __create_prompt_version_table__()
  __create_model_quality_table__()
  __create_database_schema_documentation__()

def collect_json(sql_query: str) -> str:
  dataframe_from_sql = pd.read_sql(sql_query, MY_SQL_ENGINE)
  json_from_dataframe = dataframe_from_sql.to_json()

  return json_from_dataframe

def collect_dataframe(sql_query: str, flavor: Literal['my_sql', 'postgres'] = 'my_sql') -> pd.DataFrame:

  engine = ENGINE_DICT[flavor.lower()]

  dataframe_from_sql = pd.read_sql(sql_query, engine) 

  return dataframe_from_sql

def insert(table_name: str, flavor: Literal['my_sql', 'postgres'] = 'postgres', **data):
  
  engine = ENGINE_DICT[flavor.lower()]

  columns_to_insert = list(data.keys())
  num_columns = len(columns_to_insert)
  columns_to_insert = ','.join(columns_to_insert)
  
  columns_placeholders = ','.join(['%s' for _ in range(num_columns)])

  insertion_query = (
                 f'INSERT INTO {table_name} ({columns_to_insert}) '
                 f'VALUES ({columns_placeholders})'
  )

  data_to_insert = tuple(data.values())

  connection = engine.raw_connection()
  try:
    with connection.cursor() as cursor:
        cursor.execute(insertion_query, data_to_insert)
    connection.commit()
  except Exception as e:
    connection.rollback()
    print(f"An error occurred: {e}")
  connection.close()

def describe_schema():
  database_schema_description_table = pd.read_sql('SELECT * FROM schema_documentation',
                                                  POSTGRES_ENGINE)
  
  if len(database_schema_description_table) == 0:
    database_schema_description_table = pd.read_csv(os.path.join(CURRENT_PATH,'database_schema.csv'))
    for _, r in database_schema_description_table.iterrows():
      row_dict = r.to_dict()
      insert('schema_documentation',**row_dict)

  database_schema_description = __format_schema_description__(database_schema_description_table)
  return database_schema_description

def execute_query(query: str, data: tuple = None,
                  flavor: Literal['my_sql', 'postgres'] = 'postgres'):
  
  engine = ENGINE_DICT[flavor.lower()]
  connection = engine.raw_connection()
  try:
    with connection.cursor() as cursor:
      if data is None:
        cursor.execute(query)
      else:
        cursor.execute(query, data)
    connection.commit()
  except Exception as e:
    connection.rollback()
    print(f"An error occurred: {e}")
  connection.close()


