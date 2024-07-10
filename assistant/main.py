from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from tools import database
from tools import generative
from tools import llmops

database.initialize()
generative.initialize()

PROMPT_ID = generative.PROMPT_ID
MODEL = 'model'
USER = 'user'

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=['*']
)

class AskInputModel(BaseModel):
  question: str

class ExtractInputModel(BaseModel):
  query: str

@app.post("/ask/")
def ask_to_agent(input_data: AskInputModel):
  question = input_data.question
  
  if question == '':
    output = {
            "query": '',
            "data": '',
            'explanation':'',
            "error":''
          }
    return output


  response = generative.agent(question)
  query, explanation = generative.filter(response)

  try:
    data = database.collect_json(query)
    error = None
  except Exception as e:
    data = ''
    error = str(e)

  output = {
              "query": query,
              "data": data,
              'explanation':explanation,
              "error":error
           }
  
  llmops.executinon_control(PROMPT_ID,
                            question,
                            query,
                            MODEL,
                            )


  return output

@app.post("/extract/")
def extract_from_db(input_data: ExtractInputModel):

  query = input_data.query

  try:
    data = database.collect_json(query)
    error = None
  except Exception as e:
    data = ''
    error = str(e)

  output = {
             "data": data,
             "error":error
           }

  llmops.executinon_control(PROMPT_ID,
                            '',
                            query,
                            USER,
                            )
  return output