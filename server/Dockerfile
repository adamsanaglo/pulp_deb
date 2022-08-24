FROM mcr.microsoft.com/mirror/docker/library/python:3.10-slim

ARG uid=1000
ARG gid=1000

RUN groupadd -g $gid pmc
RUN useradd -r -m -u $uid -g $gid pmc

EXPOSE 8000
WORKDIR /pmcserver

COPY pyproject.toml .
COPY poetry.lock .
COPY .env .
COPY alembic.ini .
COPY README.md .
COPY deployment/DigiCertGlobalRootCA.crt.pem .
COPY app app/
COPY migrations migrations/

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install && \
    apt-get update && \
    apt-get install -y rpm binutils gpg postgresql-client


ENTRYPOINT ["python", "app/main.py"]
