#!/bin/bash

if [ -z "$SECRETS_MOUNTPOINT" ]; then
  echo "SECRETS_MOUNTPOINT is not set or empty, not reading secrets"
elif [ ! -d "$SECRETS_MOUNTPOINT" ]; then
  echo "SECRETS_MOUNTPOINT is not a directory, not reading secrets"
else
  for path in $SECRETS_MOUNTPOINT/*; do
    # Translate some known secret names into their appropriate ENV name.
    f="$(basename $path)"
    case "$f" in
      pulpAdminPassword) name="PULP_ADMIN_PASSWORD";;
      pmcPostgresPassword) name="POSTGRES_PASSWORD";;
      pulpPostgresPassword) name="PULP_DATABASES__default__PASSWORD";;
      afQueueActionUrl) name="AF_QUEUE_ACTION_URL";;
      *) export name="$f";; # Else use the filename exactly
    esac
    echo "Exporting $SECRETS_MOUNTPOINT/$f to $name"
    export $name="$(cat $SECRETS_MOUNTPOINT/$f)"
  done
fi

if [ "$1" == "migrate" ]; then
  psql_cmd () { PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d "postgres" -c "$1"; }
  # Create the pmcserver database if it doesn't already exist. Executes first time per env.
  psql_cmd "SELECT datname FROM pg_catalog.pg_database WHERE datname='$POSTGRES_DB'" | grep -q $POSTGRES_DB
  if [ $? -eq 1 ]; then
    psql_cmd "create database $POSTGRES_DB"
  fi

  # Upgrade pmcserver schema.
  alembic upgrade head

  # Create the pulp database/user if they don't already exist. Executes first time per env.
  psql_cmd "SELECT datname FROM pg_catalog.pg_database WHERE datname='pulp'" | grep -q pulp
  if [ $? -eq 1 ]; then
    psql_cmd "create user pulp with encrypted password '$PULP_DATABASES__default__PASSWORD'"
    psql_cmd 'create database pulp owner pulp'
    psql_cmd 'grant all privileges on database pulp to pulp'
  fi
else
  python3 app/main.py
fi
