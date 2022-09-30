#!/bin/bash
# This script depends on the az cli and docker commands already being installed. If you
# don't have them already then take a minute an install them.
# az cli: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
. ./shared.sh

set_initial_vars "${1}"

# secrets
PULP_ADMIN_PASSWORD=$(openssl rand -base64 12)
PMC_POSTGRES_PASSWORD=$(openssl rand -base64 12)
PULP_POSTGRES_PASSWORD=$(openssl rand -base64 12)
PULP_SECRET=$(openssl rand -base64 50)
PULP_SYMMETRIC_KEY=$(openssl rand -base64 32)

# create the basic resources
az account set -s $sub
az group create --name $rg --location $region
# ... create vnet
az network vnet create -g $rg  -n $vnet --address-prefix 10.1.0.0/16 --subnet-name $aks_subnet --subnet-prefix 10.1.4.0/22
az network vnet subnet create -g $rg --vnet-name $vnet -n $pg_subnet --address-prefixes 10.1.8.0/24
az network vnet subnet update -g $rg --vnet-name $vnet --name $aks_subnet --service-endpoints "Microsoft.KeyVault"
# The tr command may not be necessary in all setups, but in my case the az command is installed
# in windows and is leaving in an extra \r character which blows everything up.
aks_sub_id=$(az network vnet subnet show -g $rg --vnet-name $vnet --name $aks_subnet --query id -o tsv | tr -d '\r')

# create storage accounts for pulp artifacts (bstg) and for storage access logs (lstg)
# Enable blob access logging on bstg; logs are written to lstg
# Create the "pulp" container in bstg
az storage account create -n $lstg -g $rg -l $region --sku Standard_RAGRS --assign-identity
az storage account create -n $bstg -g $rg -l $region --sku Standard_RAGRS --assign-identity
bstgid=$(az storage account show -g $rg -n $bstg --query id --out tsv | tr -d '\r')
bstgblobsvcid="${bstgid}/blobServices/default"
az monitor diagnostic-settings create --name pulpStorageLogs --storage-account $lstg --resource $bstgblobsvcid --logs '@log_analytics_settings.json'
bstgkey=$(get_blob_storage_key key1)
az storage container create --account-name $bstg --account-key $bstgkey -n pulp

# ... create and setup keyvault
az keyvault create --location $region -g $rg --name $kv
az keyvault network-rule add --name $kv --vnet-name $vnet --subnet $aks_subnet
# add SAW datacenter ip ranges to allow access from SAWs
# https://microsoft.sharepoint.com/sites/Security_Tools_Services/SitePages/SAS/SAW%20KB/SAW-datacenter-IP-ranges.aspx
az keyvault network-rule add --name $kv --ip-address 157.58.216.64/26 207.68.190.32/27 13.106.78.32/27 194.69.119.64/26 13.106.174.32/27 167.220.249.128/26 13.106.4.96/27
# You may also want to add (and later remove) a network rule for your ip address here so that you can complete the next steps
az keyvault update --name $kv --default-action Deny
az keyvault secret set --vault-name $kv --name pulpAdminPassword --value $PULP_ADMIN_PASSWORD
az keyvault secret set --vault-name $kv --name pmcPostgresPassword --value $PMC_POSTGRES_PASSWORD
az keyvault secret set --vault-name $kv --name pulpPostgresPassword --value $PULP_POSTGRES_PASSWORD
az keyvault secret set --vault-name $kv --name pulpSecret --value "$PULP_SECRET"
az keyvault secret set --vault-name $kv --name pulpSymmetricKey --value $PULP_SYMMETRIC_KEY
az keyvault secret set --vault-name $kv --name pulpBlobStorageKey --value $bstgkey
unset bstgkey


# ... create container registry
az acr create -g $rg --name $acr --sku Standard --location $region --admin-enabled  # --zone-redundancy is in preview, should we use it?

# ... create postgres server
az postgres flexible-server create -g $rg -n $pg --version 13 --high-availability Enabled --vnet $vnet --subnet $pg_subnet --admin-user pmcserver --admin-password $PMC_POSTGRES_PASSWORD

# ... create kubernetes cluster, attach to keyvault, grab credentials for kubectl
# Will have to JIT to "Owner" of the subscription to perform this operation, both for creating the necessary vnet roles and for attaching the acr.
az aks create -g $rg -n $aks --enable-addons monitoring --location $region \
    --node-vm-size standard_d4ds_v4 --vnet-subnet-id $aks_sub_id --zones 1 2 3 --attach-acr $acr \
    --enable-cluster-autoscaler --min-count 2 --max-count 6
az aks enable-addons -g $rg --name $aks --addons=azure-keyvault-secrets-provider --enable-secret-rotation
get_az_cli_vars

az keyvault set-policy -n $kv --key-permissions get --spn $CLIENT_ID
az keyvault set-policy -n $kv --secret-permissions get --spn $CLIENT_ID
az keyvault set-policy -n $kv --certificate-permissions get --spn $CLIENT_ID

az aks install-cli
get_aks_creds

# Push our pmcserver_api container into the registry
az acr login --name $acr
docker tag pmcserver_api $loginserver/pmcserver_api
docker push $loginserver/pmcserver_api

# Run deployment
apply_kube_config config.yml  # substitutes the environment variables in the file and sets up prerequisits

# Apply migrations in a one-off container
apply_migrations

# Start the api-pod
apply_kube_config api-pod.yml  # the only env variable substition here is the ACR loginserver. Is there a way to do that automatically?
apply_kube_config worker-pod.yml

# Create initial Account_Admin and and register the signing services.
create_initial_account
configureSigningServices

# Scale everything up
kubectl autoscale deployment api-pod --min=2 --max=3
kubectl autoscale deployment worker-pod --min=2 --max=10
kubectl autoscale deployment pulp-content --min=2 --max=10

# Get the ip address of the api and content service
echo "PMC Server is listening at http://$(get_service_ip pmc-service)/api/"
echo "Pulp content will be served at http://$(get_service_ip pulp-content)/pulp/content/"
