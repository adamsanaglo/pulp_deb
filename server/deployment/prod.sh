#!/bin/bash -e
# anything that we'll use in envsubst later must be exported
export region="eastus"
export sub="ae06cb0d-47c5-420b-ac59-8e84bef194bb"
export account_id="aa4bbdc3-cf46-4358-bd02-3d16763de2e9"  # the account of the client principals we're using
export destination_env="packages.microsoft.com"  # Pulp uses this to construct distribution base_url.
export api_hostname="pmc-ingest.trafficmanager.net"  # hostname of the pmc api
export prefix="pmc-prod"
export esrp_app_id="5af33d37-5ce6-40ea-b8c8-9129cb5f8726"
export pmcAppId="d48bb382-20ec-41b9-a0ea-07758a21ccd0"
export legacyKeyThumprint="B02C46DF417A0893"
export esrpKeyCode="CP-450779-Pgp"
export bstg="pmcprodblobstorage"
export esrpAuthCert="esrp-auth-prod"
export esrpAuthCertPath="/mnt/secrets/${esrpAuthCert}"
export esrpSignCert="esrp-sign-prod"

function env_overrides() {
    export rg="pmcprod"
    export kv="pmcprod"
    export acr="pmcprod"
    export api_cert_name="pmcIngestTLS"  # name of the tls certificate in the keyvault
    export content_cert_name="pmcDistroTLS"
    export min_pulp_workers="10"
    export min_pulp_content="4"
}
