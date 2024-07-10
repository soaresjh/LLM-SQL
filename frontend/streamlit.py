import requests

import streamlit as st
from pandas import read_json

TITLE = 'Database Analisy'
FIRST_BOX_TITLE = 'Faça uma pergunta,'
FIRST_BOX_DESC = "para submeter precione ctrl+enter:"

BASE_URL = 'http://localhost:4001'

st.title(TITLE)

if 'question' not in st.session_state:
  st.session_state.question = ''

st.write(FIRST_BOX_TITLE)
question = st.text_area(FIRST_BOX_DESC)
query = ""

col1, col2 = st.columns([1,2])

ss_question = st.session_state.question

explanation = ''
if question != st.session_state.question:
  payload = {'question':question}
  response = requests.post(f'{BASE_URL}/ask/', json=payload).json()

  query = response['query']
  data = response['data']
  explanation = response['explanation']
  error = response['error']
  st.session_state.query = query

  with col2:
    if error:
      st.session_state.show_markdown = True
      markdown = st.markdown(error)
    else:
      df = read_json(data)
      st.session_state.show_table = True
      table = st.table(df)

else:
   st.session_state.show_table = False
   st.session_state.show_markdown = False

st.session_state.question = question

with col1:
  edited_query = st.text_area("SQL Query", key='query', height=200)

if edited_query != query:

  payload = {'query': edited_query}
  response = requests.post(f'{BASE_URL}/extract/', json=payload).json()
  
  data = response['data']
  error = response['error']
  print(f'{data=}')
  with col2:
    if error:
      st.session_state.show_markdown = True
      st.markdown(error)
    else:
      df = read_json(data)
      st.session_state.show_table = True
      table = st.table(df)

explanation = explanation.replace("\n","  \n")
multi = f'###Explicação da Query Proposta\n\n{explanation}'
st.markdown(multi)