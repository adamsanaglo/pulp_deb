#!/usr/bin/bash

if [[ -z "$1" || ! -d "$1" ]]; then
    echo 'Usage: ./lint.sh <project_name>'
    exit
fi
OCI_ENV_PATH="./oci_env/" oci-env test -i -p $1 lint
