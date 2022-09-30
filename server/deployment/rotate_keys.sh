#!/bin/bash
# Perform full key rotation on blob and logging storage accounts for a PMC deployment.

# This script depends on the az cli commands already being installed. If you
# don't have them already then take a minute an install them.
# az cli: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
# (Note: do NOT install them from your distro's package repository; the Azure CLI
# must be installed from a repo hosted at packages.microsoft.com)

. ./shared.sh

# define $environment, $rg, $prefix, $bstg, $lstg, $kv
set_initial_vars "$1"

if [ -z "$KEY_ROTATION_DELAY" ]; then
    KEY_ROTATION_DELAY=600
fi

# rotate the $3 key on the $2 storage account in resource group $1 and output the new key
function rotate_storage_key () {
    if [[ "$3" == "primary" ]]; then
        keyname="key1"
    else
        keyname="key2"
    fi
    az storage account keys renew -n $2 -g $1 --key $3 --query "[? keyName == '${keyname}'].value" -o tsv | tr -d '\r'
}

key1=$(get_blob_storage_key key1)
activekey=$(az keyvault secret show --vault-name ${kv} --name pulpBlobStorageKey --query value -o tsv | tr -d '\r')
# if key1 equals activekey, renew the secondary key, drop that in keyvault, wait, then renew the primary key.
# otherwise, renew the primary key, drop that in keyvault, wait, then renew the secondary key.
if [[ "${key1}" == "${activekey}" ]]; then
    inactive="secondary"
    was_active="primary"
else
    inactive="primary"
    was_active="secondary"
fi
unset key1
unset activekey
echo "KeyVault initially holds the ${was_active} key for storage account ${bstg}"

# rotate the inactive storage key on storage account $bstg and write it to keyvault
echo "Renewing ${inactive} key on storage account ${bstg}"
bstgkey=$(rotate_storage_key ${rg} ${bstg} ${inactive})
echo "Inserting new key into keyvault"
az keyvault secret set --vault-name ${kv} --name pulpBlobStorageKey --value ${bstgkey} --output none
unset bstgkey

# Update both log storage account keys. There's no need to delay between key renewals,
# as log writing is done by a privileged actor that has direct access to keys.
for key in 'primary' 'secondary'; do
    echo "Renewing ${key} key on storage account ${lstg}"
    rotate_storage_key ${rg} ${lstg} ${key} > /dev/null
done

# wait for containers to see the change and restart, then rotate the previous active key
echo "Waiting ${KEY_ROTATION_DELAY} seconds for containers to restart"
sleep $KEY_ROTATION_DELAY
echo "Renewing ${was_active} key on storage account ${bstg}"
rotate_storage_key ${rg} ${bstg} ${was_active} > /dev/null
