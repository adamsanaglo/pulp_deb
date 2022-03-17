## Dev environment

First ensure you have docker and docker compose installed.

Then run:

```
make run
```

Now try to use the v4 api with httpie:

```
http :8000/openapi.json
http :8000/api/v4/repositories
http :8000/api/v4/repositories name=test type=yum
```

### Connecting to the PMC database

```
sudo apt install postgresql-client
make dbconsole
```

## Generating .env

To manually generate an env file, you can run:

```
make .env PULP_PASSWORD=$(openssl rand -base64 12) POSTGRES_PASSWORD=$(openssl rand -base64 12)
```

Alternatively, you can copy .env.example to .env and fill in the values.
