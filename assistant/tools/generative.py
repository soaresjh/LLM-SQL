import os
import re

import requests
from typing import Tuple

from . import llmops

from dotenv import load_dotenv
load_dotenv()

from langchain_community.llms import Ollama

OLLAMA_SERVER_URL=os.getenv('OLLAMA_SERVER_URL', 'http://ollama:11434')
LLM = Ollama(model="llama3", base_url=OLLAMA_SERVER_URL, temperature=0)

PROMPT_ID, INSTRUCTIONS, INPUT = llmops.collect_production_prompt()


def __get_models__(api_url: str = 'http://ollama:11434/api/') -> list:
  response = requests.get(os.path.join(api_url, 'tags'))
  pulled_models = [r['name'] for r in response.json()['models']]

  return pulled_models

def __pull_request__(model_name: str,
                     api_url: str = 'http://ollama:11434/api/') -> str:

    model_name = f'{model_name}:latest' if ':' not in model_name else model_name

    data = {
            "name": model_name,
            "stream": False
           }

    pulled_models = __get_models__(api_url)

    if model_name not in pulled_models:
      response = requests.post(os.path.join(api_url, 'pull'),
                               json=data)
      print('pulling model: ',
            model_name)
      print('status: ',
            response.status_code)
      return response.status_code
    else:
      print('pulling model: ',
            model_name)
      print('status: ',
            'model already exists')
      return None

def initialize():
  __pull_request__('llama3')

def agent(input_question: str) -> str:
  prompt = f'{INSTRUCTIONS}\n\n{INPUT.format(question=input_question)}'
  response = LLM.generate([prompt])
  return response.dict()['generations'][0][0]['text']

def filter(input_text: str) -> Tuple[str, str]:
  query_from_input_text = re.findall('```sql([^```]*)',input_text)
  
  if len(query_from_input_text) == 0:
    return '', "Couldn't generate a SQL Query"
  query_from_input_text = query_from_input_text[0].strip()
  
  explanation_from_input = input_text.split(query_from_input_text)[1]
  explanation_from_input = explanation_from_input.replace('```','')
  explanation_from_input = explanation_from_input.strip()

  return query_from_input_text, explanation_from_input