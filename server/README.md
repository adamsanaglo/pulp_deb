## Bootstrap script
For Ubuntu server, you can use `bootstrap.sh`, which is included in this folder. 
It will install docker-engine and start a server/API instance for you. Alternatively,
use the following steps to get started.

## Generating .env

To manually generate an env file, you can run:

```
make .env
```

Alternatively, you can copy .env.example to .env and fill in the values.


## Dev environment

First ensure you have docker and docker compose installed. You must run docker-compose 1.27 or
newer. Any distro older than November 2021 will have an older version of docker-compose.

- For Ubuntu *Server*, use [docker-engine](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).

- For WSL, use [docker-desktop](https://docs.docker.com/desktop/windows/wsl).

Note that Microsoft has a site license for Docker Desktop so any warnings about having to buy a
commercial license can safely be ignored.

```
sudo apt-get update
sudo apt-get install docker docker-compose-plugin
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

### Managing your dev environment

The dev environment is set up to automatically reload the web server when it detects any code
changes. If you need to install new python dependencies or change your configuration, you can
rebuild your container with `make rebuild`.

The make file should provide commands for most of the things you will need to manage your server dev
environment. To see a list of all make commands, run `make` without any arguments.


### Viewing the API schema

To view the schema in a web browser, visit
[http://localhost:8000/redoc](http://localhost:8000/redoc).

For the interactive docs, visit [http://localhost:8000/docs](http://localhost:8000/docs).

To view the json schema from the command line:

```
http --pretty=all :8000/openapi.json | less -R
```


### Managing the database

To make changes to the database schema such as adding a new table or column, you'll need to create a
migration using alembic. First run `make shell` and then you can interact directly with alembic:

```
$ make shell
pmc@958ac5018afc:/pmcserver# alembic revision --autogenerate -m "something"
```

Once you've created the migration, you can then run `alembic upgrade head` to apply it.
Alternatively, there is a `make migrate` command that will run `alembic upgrade head` in the api
container.

Note that you will also need to run `make migrate` if you pull changes where a new migration was
added.


### Interacting directly with Pulp

With a dev setup, it's possible to interact directly with Pulp on port 8080 on localhost.

Note: You'll need to set your Pulp username and password in your
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

First, open `.env` and configure PULP_HOST to point to `http://localhost:8080` or wherever you are
serving Pulp. You'll also need to update POSTGRES_SERVER to point to `localhost`
or update your `/etc/hosts` file to point `db` to `127.0.0.1`.

Assuming you have the docker containers already running, you can run:

```
docker compose stop api
poetry install
poetry run python app/main.py
```
