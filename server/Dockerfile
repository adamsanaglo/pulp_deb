FROM mcr.microsoft.com/cbl-mariner/base/python:3.9

ARG uid=1000
ARG gid=1000

RUN tdnf install -y binutils postgresql shadow-utils

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
    poetry install


ENTRYPOINT ["python", "app/main.py"]
