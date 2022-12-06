#!/bin/bash -e
# Update the tux-dev containers
scriptdir="$(dirname ${BASH_SOURCE[0]})"
${scriptdir}/../tools/tux-sync.py
