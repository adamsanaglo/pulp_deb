#!/usr/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./clone-repos.sh <github_username>"
    exit
fi

for repo in 'pulpcore' 'pulp_deb' 'pulp_rpm' 'pulp_python' 'pulp_file' 'pulp-oci-images' \
            'oci_env' 'pulp-openapi-generator'; do
    git clone git@github.com:${1}/${repo}.git ${repo}
    pushd $repo
    git remote add upstream https://github.com/pulp/${repo}.git
    popd
done

# also do the 1-time setup of the oci environment
pushd oci_env
pip3 install -e client

cat <<EOF > compose.env
DEV_SOURCE_PATH=pulpcore:pulp_rpm:pulp_deb:pulp_python:pulp_file
COMPOSE_BINARY=docker
EOF

popd
