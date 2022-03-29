## Dev environment

First ensure you have docker and docker-compose installed.
- If you're using WSL, [install the special WSL-ready version of Docker](https://docs.docker.com/desktop/windows/wsl).
- You must run docker-compose 1.27 or newer. Any distro older than November 2021 will have an older version of docker-compose, so you'll need to [install it from docker.com](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).

```
sudo apt-get update
sudo apt-get install docker docker-compose
```

Then run:

```
make run
```

Now try to use the v4 api with httpie:

```
http :8000/openapi.json
http :8000/api/v4/repositories/
http :8000/api/v4/repositories/ name=test type=yum
```

## Generating .env

To manually generate an env file, you can run:

```
make .env PULP_PASSWORD=$(openssl rand -base64 12) POSTGRES_PASSWORD=$(openssl rand -base64 12)
```

Alternatively, you can copy .env.example to .env and fill in the values.
