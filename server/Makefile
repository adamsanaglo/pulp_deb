include .env
SHELL := /bin/bash
PULP_PASSWORD ?= $(shell openssl rand -base64 12)
POSTGRES_PASSWORD ?= $(shell openssl rand -base64 12)

.PHONY: run build rebuild down teardown migrate shell lint dbconsole

.env:
	@echo "Creating .env file"
	cp .env.example .env
	@sed -i 's#PULP_PASSWORD=""#PULP_PASSWORD="${PULP_PASSWORD}"#' .env
	@sed -i 's#POSTGRES_PASSWORD=""#POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"#' .env

run:
	docker-compose up -d
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

build:
	docker-compose build

rebuild:
	docker-compose up -d --build
	docker exec -it pmcserver alembic upgrade head
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

down:
	docker-compose down

teardown: down
	# tear down the containers and volumes
	for vol in pulp_storage pgsql containers postgres-data; do \
		docker volume rm pmcserver_$$vol ; \
	done

migrate:
	docker exec -it pmcserver alembic upgrade head

shell:
	docker exec -it pmcserver /bin/bash

lint: run
	docker exec -it pmcserver flake8 .
	docker exec -it pmcserver isort -c .
	docker exec -it pmcserver mypy .

dbconsole:
	docker exec -it db psql -U ${POSTGRES_USER}
