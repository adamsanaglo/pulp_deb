psql -U $POSTGRES_USER -c "create user pulp with encrypted password '$PULP_DATABASES__default__PASSWORD'"
psql -U $POSTGRES_USER -c 'create database pulp'
psql -U $POSTGRES_USER -c 'grant all privileges on database pulp to pulp'