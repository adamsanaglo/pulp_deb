#!/bin/bash -e
shopt -s expand_aliases
if [ -z "$1" ]; then
  echo 'usage: update.sh "ppe|tux|prod" [<yml-file>]'
  echo 'If $2 is not provided then all yaml files will be applied.'
  exit
fi
. ./shared.sh

set_initial_vars "${1}"
get_az_cli_vars
get_aks_creds
if [ -z "$2" ]; then
  apply_kube_config config.yml
  apply_migrations
  apply_kube_config api-pod.yml
  apply_kube_config worker-pod.yml
  apply_kube_config ingress.yml
  kubectl rollout restart deployment api-pod
  kubectl rollout restart deployment worker-pod
  kubectl rollout restart deployment pulp-content
else
  apply_kube_config $2
fi
