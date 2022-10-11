#!/bin/bash -e
export region="eastus"
export sub="e4b53a57-a6fe-4389-8eb2-64a14bef28bd"
export account_id="55248ac4-3ce8-4a2b-abe8-beb7c641a7a2"  # the account of the client principals we're using
export destination_env="tux-devrepo.corp.microsoft.com"  # Pulp uses this to construct distribution base_url.
export prefix="pmc-tux"
export esrp_app_id="d8309de1-3c8f-4e2c-a8f8-d61d6e5a75ba"
export pmcAppId="55391a9d-3c3b-4e4a-afa6-0e49c2245175"
export legacyKeyThumprint="C5E3FD35A3A036D0"
export esrpKeyCode="CP-450779-Pgp"
export bstg="pmctuxblobstorage"

function env_overrides() {
    # None
}
