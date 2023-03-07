#!/bin/bash -e
# anything that we'll use in envsubst later must be exported
export region="eastus"
export sub="0647ab1e-ce75-49ed-9b77-9e514021282b"
export account_id="4f5e359d-dfd5-4137-9324-63dc4a639fe8"  # the account of the client principals we're using
export destination_env="csd.packages.ppe.trafficmanager.net"  # Pulp uses this to construct distribution base_url.
export api_hostname="csd-apt-cat-ppe.westus2.cloudapp.azure.com"  # hostname of the pmc api
export prefix="pmc-ppe"
export esrp_app_id="754be256-20b9-443e-b73c-0977d72f16dc"
export pmcAppId="1ce02e3e-1bf3-4d28-8cdc-e921f824399d"
export legacyKeyThumprint="C8D312C8D46CB3CF"
export esrpKeyCode="CP-450778-Pgp"
export esrpAuthCert="esrp-auth-test"
export esrpSignCert="esrp-sign-test"

function env_overrides() {
    export kv="${prefix}-keyvault-51689"
    export api_cert_name="apt-ppe-api-ssl"  # name of the tls certificate in the keyvault
    export content_cert_name="apt-ppe-ssl-new"
    export aks_upgrade_policy="rapid"
}