SHELL := /bin/bash
.PHONY: help run build rebuild down teardown update reset migrate shell lint dbconsole clear_env rebuild_env

default: help

run:				## run the dev container 
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env compose up -d

build:		 		## build the container images
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env compose build

rebuild: 			## rebuild the container images and run them
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env compose up -d --build

down:				## stop and remove the containers
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env compose down

teardown: 			## stop the containers and remove the container volumes
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env compose down --volumes

shell:				## open a bash console to the pulp container
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env exec bash

dbconsole:			## open a psql console and connect to the database
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env exec psql -U pulp

pulpconsole:           ## open a console for debugging pulp
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env exec bash -c "pip install -q django-extensions"
	OCI_ENV_PATH="$(CURDIR)/oci_env/" oci-env exec bash -c "pulpcore-manager shell_plus"

logs:			## watch the logs
	docker logs -f oci_env-pulp-1

help:
	@echo 'usage: make [target] ...'
	@echo
	@echo 'targets:'
	@gawk '/^\S.*:.*##/ { print gensub(/^([[:alnum:]\._]+):.*##\s+(.*)/, "\\1: \\2", "g") }' $(MAKEFILE_LIST)
