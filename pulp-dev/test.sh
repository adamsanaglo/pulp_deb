#!/usr/bin/bash

if [[ -z "$1" || ! -d "$1" ]]; then
    echo 'Usage: ./test.sh <project_name> [<test_name>] [--setup]'
    echo "--setup is required the first time after a rebuild to install dependencies," \
         "but subsequent runs don't need it."
    exit
fi

PROJECT=$1
INSTALL_DEPS=""
TEST="$2"

setup () {
   INSTALL_DEPS="-i"
   # "oci-env generate-client" ignores the OCI_ENV_PATH for some reason, so we actually have to cd
   pushd oci_env
   oci-env generate-client -i
   popd
}

if [ "$2" == "--setup" ]; then
   setup
   TEST="$3"
elif [ "$3" == "--setup" ]; then
   setup
fi

if [ ! -z "$TEST" ]; then
   TEST="-k $TEST"
fi

OCI_ENV_PATH="./oci_env/" oci-env test $INSTALL_DEPS -p $PROJECT functional $TEST
