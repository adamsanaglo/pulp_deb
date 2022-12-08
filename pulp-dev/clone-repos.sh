#!/usr/bin/bash

if [ -n "$1" ]; then
    echo "Usage: ./clone-repos.sh <github_username>"
fi

for repo in 'pulpcore' 'pulp_deb' 'pulp_rpm' 'pulp_python' 'pulp_file' 'pulp-oci-images'; do
    git clone git@github.com:${1}/${repo}.git
    pushd $repo
    git remote add upstream https://github.com/pulp/${repo}.git
    popd
done
