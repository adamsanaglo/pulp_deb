#!/bin/bash -e
env="$1"
oldNodepool="nodepool1"
newNodepool="nodepool2"
declare -A maxNodes=( ["ppe"]="7" ["prod"]="30" )
vmSku="standard_d4ds_v4"
usage() {
    echo "Migrate AKS nodepool to Mariner OS image
$0 ENV
    ENV Environment for this deployment (ppe|prod)"
    exit 1
}

prerequisites() {
    # Upgrade to Mariner requires aks-preview extension

    # Upgrade to latest az cli
    az upgrade --y
    
    # Remove previous extension if present
    ! az extension remove --name aks-preview
    
    # Use latest AKS extension
    az extension add --name aks-preview

    # Install kubectl if not present
    if ! which kubectl > /dev/null; then
        az aks install-cli
    fi
}

createNodepool() {
    # Creates a new Mariner-based nodepool
    subnet_id="/subscriptions/$sub/resourceGroups/$rg/providers/Microsoft.Network/virtualNetworks/$vnet/subnets/$aks_subnet"
    az aks nodepool add --cluster-name $aks -n ${newNodepool} --min-count 3 --max-count ${maxNodes[$env]} -e --vnet-subnet-id $subnet_id -s $vmSku -g $rg --os-sku Mariner --mode System

    # Enable AzSecPack on the backing VMSS, to avoid security alerts
    nrg=$(az aks show -g $rg -n $aks --query nodeResourceGroup | tr -d '"')
    vmss_name=$(az vmss list -g $nrg --query '[0].name' | tr -d '"')
    az vmss update -g $nrg -n $vmss_name --set tags.AzSecPackAutoConfigReady=true
}

drainOldNodepool() {
    # Cordon and drain each node in the pool
    for node in $(kubectl get nodes | grep ${oldNodepool} | awk '{print $1}'); do
        # This code will block until the node is actually drained
        # https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/#use-kubectl-drain-to-remove-a-node-from-service
        kubectl cordon ${node}
        kubectl drain ${node} --ignore-daemonsets --delete-emptydir-data
    done
}

deleteNodepool() {
    # Delete the old nodepool
    az aks nodepool delete --resource-group $rg --cluster-name $aks --name $oldNodepool
}

if [[ -z "$env" ]]; then
    echo "Must specify environment"
    usage
elif [[ "$env" != "ppe" ]] && [[ "$env" != "prod" ]]; then
    echo "Environment must be ppe or prod"
    usage
fi

# Upgrade az aks extension
prerequisites

# Import environment variables
. ./shared.sh
set_initial_vars $env

createNodepool
drainOldNodepool
deleteNodepool