#!/bin/bash -e
# Adds apt and yum signing services.
# Only invoked once per environment/signing key
if [[ -z "${3}" ]]; then
    cat << END
USAGE: ${0} KEYTYPE SCRIPTPATH KEYPATH
    KEYTYPE:    [esrp|legacy]
    SCRIPTPATH: Path to signing script (/sign_cli/sign*)
    KEYPATH:    Path to pubkey (/sign_cli/*.asc)
END
    exit 1
fi
# Need the DB password to add the signer
source /usr/bin/pmc-secrets-exporter.sh

# The signing key must be imported
gpg --import ${3}
keyid=$(gpg --show-keys $3 | head -n 2 | tail -n 1 | tail -c 17)
/usr/local/bin/pulpcore-manager add-signing-service "${1}_yum" ${2}.py "${keyid}"
/usr/local/bin/pulpcore-manager add-signing-service "${1}_apt" ${2}_apt.py --class deb:AptReleaseSigningService "${keyid}"