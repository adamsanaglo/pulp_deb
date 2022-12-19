#!/usr/bin/bash

if [[ -z "$1" || ! -d "$1" ]]; then
    echo 'Usage: ./test.sh <project_name>'
    exit
fi
OCI_ENV_PATH="./oci_env/" oci-env generate-client -i
OCI_ENV_PATH="./oci_env/" oci-env test -i -p $1 functional
