#!/bin/bash -e
export region="eastus"
export sub="0647ab1e-ce75-49ed-9b77-9e514021282b"
export account_id="4f5e359d-dfd5-4137-9324-63dc4a639fe8"  # the account of the client principals we're using
export destination_env="packages.microsoft.com"  # Pulp uses this to construct distribution base_url.
export prefix="pmc-ppe"
export kv="${prefix}-keyvault-51689"  # anything that we'll use in envsubst later must be exported
export esrp_app_id="754be256-20b9-443e-b73c-0977d72f16dc"
export pmcAppId="1ce02e3e-1bf3-4d28-8cdc-e921f824399d"
export legacyKeyThumprint="C8D312C8D46CB3CF"
export esrpKeyCode="CP-450778-Pgp"
