## Generating .env

To manually generate an env file, you can run:

```
make .env PULP_PASSWORD=$(openssl rand -base64 12) POSTGRES_PASSWORD=$(openssl rand -base64 12)
```

Alternatively, you can copy .env.example to .env and fill in the values.


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
http :8000/api/
http :8000/api/v4/repositories/
http :8000/api/v4/repositories/ name=test type=yum
```


### Viewing the API schema

To view the schema in a web browser, visit
[http://localhost:8000/redoc](http://localhost:8000/redoc).

For the interactive docs, visit [http://localhost:8000/docs](http://localhost:8000/docs).

To view the json schema from the command line:

```
http --pretty=all :8000/openapi.json | less -R
```


### Interacting directly with Pulp

With a dev setup, it's possible to interact directly with Pulp on port 8080 on localhost.

Note: You'll want to set your Pulp username and password in your
[`.netrc`](https://www.gnu.org/software/inetutils/manual/html_node/The-_002enetrc-file.html) file or
use httpie's `--auth` option.

```
http :8080/pulp/api/v3/status/
http :8080/pulp/api/v3/repositories/
http --pretty=all :8080/pulp/api/v3/docs/api.json | less -R
```

### Running the API server outside of a container

Sometimes it may be helpful to run the API server outside of a container to make it easier to
interact with.

First, open `.env` and configure PULP_HOST to point to `http://localhost:8080` or wherever you you
are serving Pulp.

Now install the API server dependencies using poetry:

```
poetry install
```

Next, start the pulp and db services:

```
docker-compose up -d pulp db
```

Now run the api server:

```
poetry run python app/main.py
```
