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
      pulpAdminPassword) name="PULP_PASSWORD";;
      pmcPostgresPassword) name="POSTGRES_PASSWORD";;
      *) export name="$f";; # Else use the filename exactly
    esac
    echo "Exporting $SECRETS_MOUNTPOINT/$f to $name"
    export $name="$(cat $SECRETS_MOUNTPOINT/$f)"
  done
fi

python3 app/main.py