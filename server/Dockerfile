FROM python:3.9.2

ARG uid=1000
ARG gid=1000

RUN groupadd -g $gid pmc
RUN useradd -r -u $uid -g $gid pmc

EXPOSE 8000
WORKDIR /pmcserver

COPY pyproject.toml .
COPY poetry.lock .
COPY .env .
COPY alembic.ini .

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install && \
    apt-get update && \
    apt-get install -y rpm binutils

COPY app app/
COPY migrations migrations/

ENTRYPOINT ["python", "app/main.py"]
