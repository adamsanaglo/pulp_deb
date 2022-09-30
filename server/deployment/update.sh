#!/bin/bash -e
. ./shared.sh

set_initial_vars "${1}"
get_az_cli_vars
get_aks_creds
apply_kube_config config.yml
apply_migrations
apply_kube_config api-pod.yml
apply_kube_config worker-pod.yml
