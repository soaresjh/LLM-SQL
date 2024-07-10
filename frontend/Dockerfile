FROM python:3.11-bullseye

RUN pip3 install streamlit==1.35.0 requests==2.32.3 pandas==2.2.2 matplotlib==3.9.1

WORKDIR /app
COPY . /app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

## ENTRYPOINT ["streamlit", "run", "streamlit.py", "--server.port=8501", "--server.headless=true"]
## streamlit run streamlit.py --server.port=8501 --server.headless=true