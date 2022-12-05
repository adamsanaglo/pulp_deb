#!/bin/bash -e
# Login to az cli using MSI/Service Principal
scriptdir="$(dirname ${BASH_SOURCE[0]})"
${scriptdir}/../../tools/login-deploy.py
