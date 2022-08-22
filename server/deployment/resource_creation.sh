# This script depends on the az cli and docker commands already being installed. If you
# don't have them already then take a minute an install them.
# az cli: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

region='eastus'
sub='b88ca4c8-592e-4ef9-a17e-b4f29727824c'
account_id="1334b698-bee4-4556-ae45-a5e7b5698504"  # the account of the client principals we're using
destination_env="packages.microsoft.com"  # Pulp uses this to construct distribution base_url.
# These are just names and can be changed to whatever you want
prefix='pmc-ppe'
rg="${prefix}-rg"
vnet="${prefix}-vnet"
aks_subnet="${prefix}-aks-subnet"
pg_subnet="${prefix}-pg-subnet"
aks="${prefix}-kube-cluster"
acr="$(echo $prefix | tr -cd '[:alnum:]')acr"  # alphanumeric only
pg="${prefix}-pg"
export kv="${prefix}-keyvault"  # anything that we'll use in envsubst later must be exported

# secrets
PULP_PASSWORD=$(openssl rand -base64 12)
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
# The tr command may not be necessary in all setups, but in my case the az command is installed in windows and is leaving in an extra \r character which blows everything up.
aks_sub_id=$(az network vnet subnet show -g $rg --vnet-name $vnet --name $aks_subnet --query id -o tsv | tr -d '\r')
# ... create and setup keyvault
az keyvault create --location $region -g $rg --name $kv
az keyvault secret set --vault-name $kv --name pulpAdminPassword --value $PULP_PASSWORD
az keyvault secret set --vault-name $kv --name pmcPostgresPassword --value $PMC_POSTGRES_PASSWORD
az keyvault secret set --vault-name $kv --name pulpPostgresPassword --value $PULP_POSTGRES_PASSWORD
az keyvault secret set --vault-name $kv --name pulpSecret --value "$PULP_SECRET"
az keyvault secret set --vault-name $kv --name pulpSymmetricKey --value $PULP_SYMMETRIC_KEY
az keyvault network-rule add --name $kv --vnet-name $vnet --subnet $aks_subnet
# add SAW datacenter ip ranges to allow access from SAWs
# https://microsoft.sharepoint.com/sites/Security_Tools_Services/SitePages/SAS/SAW%20KB/SAW-datacenter-IP-ranges.aspx
az keyvault network-rule add --name $kv --ip-address 157.58.216.64/26 207.68.190.32/27 13.106.78.32/27 194.69.119.64/26 13.106.174.32/27 167.220.249.128/26 13.106.4.96/27
az keyvault update --name $kv --default-action Deny
# ... create container registry
az acr create -g $rg --name $acr --sku Standard --location $region --admin-enabled  # --zone-redundancy is in preview, should we use it?
# ... create kubernetes cluster, attack to keyvault, grab credentials for kubectl
# Will have to JIT to "Owner" of the subscription to perform this operation, both for creating the necessary vnet roles and for attaching the acr.
az aks create -g $rg -n $aks --enable-addons monitoring --location $region \
    --node-vm-size standard_d4ds_v4 --vnet-subnet-id $aks_sub_id --zones 1 2 3 --attach-acr $acr \
    --enable-cluster-autoscaler --min-count 2 --max-count 6
az aks enable-addons -g $rg --name $aks --addons=azure-keyvault-secrets-provider --enable-secret-rotation
export AZURE_TENANT_ID=$(az account show --query tenantId -o tsv | tr -d '\r')
export CLIENT_ID=$(az aks show -g $rg -n $aks --query addonProfiles.azureKeyvaultSecretsProvider.identity.clientId -o tsv | tr -d '\r')
az keyvault set-policy -n $kv --key-permissions get --spn $CLIENT_ID
az keyvault set-policy -n $kv --secret-permissions get --spn $CLIENT_ID
az keyvault set-policy -n $kv --certificate-permissions get --spn $CLIENT_ID
az aks install-cli
az aks get-credentials -g $rg --name $aks
# ... create postgres server
az postgres flexible-server create -g $rg -n $pg --version 13 --high-availability Enabled --vnet $vnet --subnet $pg_subnet --admin-user pmcserver --admin-password $PMC_POSTGRES_PASSWORD
export pg_server=$(az postgres flexible-server show -g $rg -n $pg --query 'fullyQualifiedDomainName' -o tsv | tr -d '\r')

# Push our pmcserver_api container into the registry
az acr login --name $acr
export loginserver=$(az acr show -g $rg --name $acr --query 'loginServer' -o tsv | tr -d '\r')
docker tag pmcserver_api $loginserver/pmcserver_api
docker push $loginserver/pmcserver_api

# run deployment
envsubst < config.yml | kubectl apply -f -  # substitutes the environment variables in the file and sets up prerequisits
envsubst < api-pod.yml | kubectl apply -f -  # the only env variable substition here is the ACR loginserver. Is there a way to do that automatically?
 
# Init pmc db and prep for pulp access
PMCPOD=$(kubectl get pod -l app=pmc -o jsonpath="{.items[0].metadata.name}")
alias pmc_run="kubectl exec --stdin -c pmc --tty $PMCPOD -- /bin/bash -c"
pmc_run "PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver -d postgres -c 'create database pmcserver'"
pmc_run "alembic upgrade head"
pmc_run "PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver -d pmcserver -c \"insert into account (id, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited) values ('$account_id', 'dev', 'Account_Admin', 'dev', 'dev', 'dev@user.com', 't', now(), now())\""
pmc_run "PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver -d postgres -c \"create user pulp with encrypted password '$PULP_POSTGRES_PASSWORD'\""
pmc_run "PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver -d postgres -c 'create database pulp'"
pmc_run "PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver -d postgres -c 'grant all privileges on database pulp to pulp'"

# restart the deployment so that pulp-api will actally connect to the db and create schema
kubectl rollout restart deployment api-pod

# Give pulp-api about 5 minutes to create the schema, then start pulp-worker and scale everything up
envsubst < worker-pod.yml | kubectl apply -f -
kubectl autoscale deployment api-pod --min=2 --max=3
kubectl autoscale deployment worker-pod --min=2 --max=10
kubectl autoscale deployment pulp-content --min=2 --max=10

# Get the ip address of the api and content service
echo "PMC Server is listening at http://$(kubectl get service/pmc-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/api/"
echo "Pulp content will be served at http://$(kubectl get service/pulp-content -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/pulp/content/"