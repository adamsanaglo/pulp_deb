#!/usr/bin/bash
# Creates a branch by checking out the supplied project tag and applying our image patches on top.
# Useful for building patches and testing locally.
# You must supply the release tag to check out, look for version locks in ../pulp/Dockerfile .

if [ $# -ne 3 ]; then
    echo "Usage: ./create-branch.sh <project> <project_base_version> <new_branch_name>"
    echo "Example: ./create-branch.sh 'pulp_deb' '2.20.0' 'new_awesome_branch'"
    exit
fi

pushd $1
git fetch upstream
git checkout -b $3 $2
git am ../../pulp/container-assets/$1/*.patch
popd
