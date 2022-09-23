#!/bin/bash -e
. ./shared.sh

if [[ -z "${1}" ]]; then
    bail "Must specify environment (ppe); tux|prod not yet supported"
elif [[ "${1}" == "ppe" ]]; then
    . ./ppe.sh
else
    bail "Environment '${1}' not supported"
fi


set_initial_vars
get_az_cli_vars
get_aks_creds
apply_kube_config config.yml
apply_migrations
apply_kube_config api-pod.yml
apply_kube_config worker-pod.yml
