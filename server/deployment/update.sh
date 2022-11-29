#!/bin/bash -e
shopt -s expand_aliases
if [ -z "$1" ]; then
  echo 'usage: update.sh "ppe|tux|prod" [api-pod|worker-pod|pulp-content|nginx-api|nginx-content]' \
       '[<yml-file>]'
  echo 'If the optional args are not provided then all yaml files will be applied, migrations' \
       'run, and all containers will be bounced.'
  echo 'Or you can only roll a pod (to pick up new released images) by providing $2.'
  echo 'Or you can apply one yml file and then bounce the specified pod by providing $2 and $3.'
  exit
fi
. ./shared.sh

set_initial_vars "${1}"
get_az_cli_vars
get_aks_creds

# Update all
if [ -z "$2" ]; then
  apply_kube_config config.yml
  apply_migrations
  apply_kube_config api-pod.yml
  apply_kube_config worker-pod.yml
  apply_kube_config ingress.yml
  kubectl rollout restart deployment api-pod
  kubectl rollout restart deployment worker-pod
  kubectl rollout restart deployment pulp-content
  kubectl rollout restart deployment nginx-api
  kubectl rollout restart deployment nginx-content
  exit
fi

# If we're here they've specified a pod to bounce. If there's a yml file to deploy do that first.
if [ ! -z "$3" ]; then
  apply_kube_config $3
fi

kubectl rollout restart deployment $2