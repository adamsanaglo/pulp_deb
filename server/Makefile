include .env
SHELL := /bin/bash
PULP_PASSWORD ?= $(shell openssl rand -base64 12)
POSTGRES_PASSWORD ?= $(shell openssl rand -base64 12)

.PHONY: help run build rebuild down teardown update reset migrate shell lint dbconsole

default: help

.env:				## generate an .env file from .env.example
	@echo "Creating .env file"
	cp .env.example .env
	@sed -i 's#PULP_PASSWORD=""#PULP_PASSWORD="${PULP_PASSWORD}"#' .env
	@sed -i 's#POSTGRES_PASSWORD=""#POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"#' .env

run:				## run the containers
	docker compose up -d
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

build:				## build the container images
	docker compose build

rebuild:			## rebuild the container images and run them
	docker compose up -d --build
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

down:				## stop and remove the containers
	docker compose down

teardown: down		## stop the containers and remove the container volumes
	for vol in pulp_storage pgsql containers postgres-data; do \
		docker volume rm pmcserver_$$vol ; \
	done

update:				## pull the latest images and run the containers
	docker compose pull
	docker compose up -d
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

reset: teardown		## remove container volumes and restart containers
	docker compose up -d
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

migrate:			## apply any database migrations to the api container
	docker exec -it pmcserver alembic upgrade head

shell:				## open a bash console to the api container
	docker exec -it pmcserver /bin/bash

lint: run			## run the lint checks in the api container
	docker exec -it pmcserver flake8 .
	docker exec -it pmcserver isort -c .
	docker exec -it pmcserver mypy .

dbconsole:			## open a psql console and connect to the database
	docker exec -it db psql -U ${POSTGRES_USER}

help:
	@echo 'usage: make [target] ...'
	@echo
	@echo 'targets:'
	@gawk '/^\S.*:.*##/ { print gensub(/^([[:alnum:]\.]+):.*##\s+(.*)/, "\\1: \\2", "g") }' $(MAKEFILE_LIST)
