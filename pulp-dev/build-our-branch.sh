#!/usr/bin/bash
# Creates a branch by checking out the supplied project tag and applying our image patches on top.
# Useful for building patches and testing locally.
# You must supply the release tag to check out, look for version locks in ../pulp/Dockerfile .

if [ $# -ne 3 ]; then
    echo "Usage: ./build-our-branch.sh <project> <project_base_version> <new_branch_name>"
    echo "Example: ./build-our-branch.sh 'pulp_deb' '2.20.0' 'new_awesome_branch'"
    exit
fi

pushd $1
git fetch upstream
git checkout $2
git switch -c $3
git am ../../pulp/container-assets/$2/*.patch
popd
