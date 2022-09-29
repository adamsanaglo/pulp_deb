#!/bin/bash -e
. ./shared.sh

environment=${1}
if [[ -z "${environment}" ]]; then
    bail "Must specify environment (ppe|tux|prod)"
elif [[ "${environment}" == "ppe" ]] || [[ "${environment}" == "tux" ]] || [[ "${environment}" == "prod" ]]; then
    . ./${environment}.sh
else
    bail "Environment '${environment}' not supported"
fi


set_initial_vars
get_az_cli_vars
get_aks_creds
apply_kube_config config.yml
apply_migrations
apply_kube_config api-pod.yml
apply_kube_config worker-pod.yml
