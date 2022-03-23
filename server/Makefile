include .env
SHELL := /bin/bash
PULP_PASSWORD ?= $(openssl rand -base64 12)
POSTGRES_PASSWORD ?= $(openssl rand -base64 12)

.PHONY: generate_env run build reset down lint dbconsole

.env:
	@echo "Creating .env file"
	cp .env.example .env
	@sed -i 's#PULP_PASSWORD=""#PULP_PASSWORD="${PULP_PASSWORD}"#' .env
	@sed -i 's#POSTGRES_PASSWORD=""#POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"#' .env

run:
	docker-compose up -d
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

build:
	docker-compose build

rebuild:
	docker-compose up -d --build
	@docker exec -it pulp bash -c 'pulpcore-manager reset-admin-password -p ${PULP_PASSWORD}'

reset: down rebuild

down:
	docker-compose down

lint: run
	docker exec -it pmcserver flake8 .
	docker exec -it pmcserver isort -c .
	docker exec -it pmcserver mypy --strict .

dbconsole:
	docker exec -it postgres psql -U ${POSTGRES_USER}
