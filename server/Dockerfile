FROM mcr.microsoft.com/cbl-mariner/base/python:3.9

ARG uid=1000
ARG gid=1000
ARG dev=0
ENV dev $dev

RUN tdnf install -y binutils postgresql shadow-utils util-linux vim ca-certificates

RUN groupadd -g $gid pmc
RUN useradd -r -m -u $uid -g $gid pmc

EXPOSE 8000
WORKDIR /pmcserver

COPY pyproject.toml .
COPY poetry.lock .
COPY alembic.ini .
COPY README.md .
COPY deployment/root-cert-bundle.pem .
COPY deployment/entrypoint.sh .
COPY app app/
COPY migrations migrations/

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    if [[ $dev == 1 ]]; then POETRY_OPTS=(); else POETRY_OPTS=(--without dev); fi && \
    poetry install "${POETRY_OPTS[@]}"


ENTRYPOINT ["./entrypoint.sh"]
