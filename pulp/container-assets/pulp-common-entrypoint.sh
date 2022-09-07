#!/bin/bash

# Prevent pip-installed /usr/local/bin/pulp-content from getting run instead of
# our /usr/bin/pulp script.
#
# We still want conatiner users to call pulp-* command names, not paths, so we
# can change our scripts' locations in the future, and call special logic in this
# script based solely on theo command name.

## PMC addition: read secrets from the KeyVault into env variables
source /usr/bin/pmc-secrets-exporter.sh

if [[ "$@" = "pulp-content" || "$@" = "pulp-api" || "$@" = "pulp-worker" || "$@" = "pulp-resource-manager" ]]; then
        exec "/usr/bin/$@"
else
        exec "$@"
fi
