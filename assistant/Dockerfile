FROM python:3.11-bullseye

WORKDIR /home

RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/pip-tmp/
RUN pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

COPY . /home/app

EXPOSE 5001

## CMD ["fastapi", "run", "app/main.py", "--port", "5001"]