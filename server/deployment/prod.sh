#!/bin/bash -e
# anything that we'll use in envsubst later must be exported
export region="eastus"
export sub="ae06cb0d-47c5-420b-ac59-8e84bef194bb"
export account_id="aa4bbdc3-cf46-4358-bd02-3d16763de2e9"  # the account of the client principals we're using
export destination_env="packages.microsoft.com"  # Pulp uses this to construct distribution base_url.
export api_hostname="pmc-ingest.trafficmanager.net"  # hostname of the pmc api
export prefix="pmc-prod"
export esrp_app_id="34bd9bc3-d07f-4f29-81db-64e98f469905"
export pmcAppId="b6eedb70-8c44-4683-afd3-0d6c9b299803"
export legacyKeyThumprint="B02C46DF417A0893"
export esrpKeyCode="CP-450779-Pgp"
export bstg="pmcprodblobstorage"
export esrpAuthCert="esrp-auth-prod"
export esrpSignCert="esrp-sign-prod"

function env_overrides() {
    export rg="pmcprod"
    export kv="pmcprod"
    export acr="pmcprod"
}
