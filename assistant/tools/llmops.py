from . import database
from datetime import date, datetime

from typing import Literal

DEFUALT_INSTRUCTIONS = '''Your task is to convert a question into a SQL query, given a MySQL database schema.
Adhere to these rules:
- Deliberately go through the question and database schema word by word** to appropriately answer the question
- Use Table Aliases to prevent ambiguity. For example, `SELECT table1.col1, table2.col1 FROM table1 JOIN table2 ON table1.id = table2.id`.
- Make sure that every table you are using exists in the database.
'''

DEFAULT_INPUT = '''Generate a SQL query that answers the question: {question}.
This query will run on a database whose schema is represented in this string:

'''+database.describe_schema()+\
'''### Response:
Based on your instructions, here is the SQL query I have generated to answer the question `{question}`:'''


def collect_production_prompt():

  prompt_table = database.collect_dataframe('SELECT * FROM prompt_version', 'postgres')
  prompt_table = prompt_table.query('status=="production"')

  if len(prompt_table) == 0:

    prompt_data = {'prompt_instructions':DEFUALT_INSTRUCTIONS,
                   'prompt_input':DEFAULT_INPUT,
                   'base_llm_name': 'llama3',
                   'status':'production',
                   'creation_date':date.today(),
                   'to_production_date':date.today()
                   }

    database.insert('prompt_version', **prompt_data)

    prompt_ids = prompt_table['prompt_id']

    prompt_id = 0 if prompt_ids.empty else prompt_ids.max()+1
    instructions = DEFUALT_INSTRUCTIONS
    inputing = DEFAULT_INPUT

  else:
    [prompt_id, instructions, inputing] = prompt_table.iloc[0][['prompt_id',
                                                             'prompt_instructions',
                                                             'prompt_input']].values
    prompt_id = int(prompt_id)

  return prompt_id, instructions, inputing

def executinon_control(prompt_id: int,
                       input_information: str,
                       output_model: str,
                       source: Literal['model', 'user'],
                       user_id: int=0):

  execute_data = {
                  'prompt_id':prompt_id,
                  'input_information':input_information,
                  'output_model':output_model,
                  'source':source,
                  'user_id':user_id,
                  'created_at':datetime.now()
                }

  database.insert('model_quality',**execute_data)

def move_model_to_production(model_id: int):
  
  from_production_to_archive_query = """
    UPDATE prompt_version
    SET status = %s, to_archive_date = %s
    WHERE status = 'production' AND prompt_id <> %s;
    """
  database.execute_query(from_production_to_archive_query,
                         ('archived', date.today(), model_id))
  
  to_production_query = """
    UPDATE prompt_version
    SET status = %s, to_production_date = %s
    WHERE prompt_id = %s;
    """
  database.execute_query(to_production_query,
                         ('production', date.today(), model_id))