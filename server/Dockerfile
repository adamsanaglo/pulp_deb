FROM python:3.9.2

EXPOSE 8000
WORKDIR /pmcserver

COPY pyproject.toml .
COPY poetry.lock .
COPY .env .

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install

COPY app app/

ENTRYPOINT ["python", "app/main.py"]
