#!/usr/bin/bash
# This helper script cds into the project you specify, does a "git format-patch" on the most
# recent commit (and using the number you specified), and puts it in the appropriate place in
# ../pulp. You are then expected to add it to the Dockerfile yourself and rebuild.

if [ $# -lt 2 ]
then
  echo "Usage: ./make-patch.sh <patch-number> <project>"
  exit
fi

pushd $2
mkdir -p ../../pulp/container-assets/$2
git format-patch --start-number $1 -1 --relative $2
mv *.patch ../../pulp/container-assets/$2
popd