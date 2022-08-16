#!/bin/bash -e
# Creates the resources used by the status monitor, and deploys
# the Azure Function code to run in Azure.

resourceGroup=statusmonitor
resourceGroupPremiumAppService=${resourceGroup}-premium
location=centralus
storageAccount=pmcstatus
consumption=consumption # Low-cost Azure Function offering
premium=premium         # Upper tier Azure Function offering
appPlans=(${consumption} ${premium} ${consumption})
dirNames=("pmc_scan_mirrors" "pmc_scan_repos" "pmc_status_delivery")
skuStoragePrimary="Standard_RAGRS"
skuStorageSecondary="Standard_LRS"
functionsVersion="4"

function bail() {
    >&2 echo "${@}"
    exit 1
}

function createResourceGroups() {
    echo "Creating $resourceGroup in "$location"..."
    az group create --name $resourceGroup --location "$location"

    # Create resource group for the premium app service plan
    echo "Creating $resourceGroupPremiumAppService in "$location"..."
    az group create --name $resourceGroupPremiumAppService --location "$location"
}

function createPrimaryStorage() {
    # Create Primary Storage Account that will host our website
    az storage account create -n ${storageAccount} -g ${resourceGroup} -l ${location} --sku $skuStoragePrimary
}

function configurePrimaryStorage() {
    # Configure the primary storage account that serves as the center piece of status monitoring
    az storage cors add --connection-string $primarystorage_connectionstring --origins '*' --methods GET --allowed-headers '*' --exposed-headers 'Content-Length' --max-age 5 --services b
    
    echo "Creating storage container dynamic-public-data"
    az storage container create --connection-string $primarystorage_connectionstring --name dynamic-public-data --public-access blob
    az storage blob upload --connection-string $primarystorage_connectionstring --container-name dynamic-public-data --name repository_status.json --file files/repository_status.json

    echo "Creating storage container static-data"
    az storage container create --connection-string $primarystorage_connectionstring --name static-data
    az storage blob upload --connection-string $primarystorage_connectionstring --container-name static-data --name mirrors.json --file files/mirrors.json
    az storage blob upload --connection-string $primarystorage_connectionstring --container-name static-data --name pubkeys.json --file files/pubkeys.json

    echo 'Creating storage container $web'
    az storage container create --connection-string $primarystorage_connectionstring --name '$web'

    pushd website/ > /dev/null
    az storage blob upload-batch -s site-content/ -d '$web' --account-name ${storageAccount} --overwrite --auth-mode key
    popd > /dev/null
    az storage blob service-properties update --account-name ${storageAccount} --static-website --404-document 404.html --index-document mirror.html --auth-mode login
}

function createAppServicePlan() {
    # Create premium app service plan, which will hold a single function (pmcscanrepos)
    # Must exist in a separate resource group to separate it from consumption plan(s)
    # Consumption plans are created automatically when functions are created
    skuPlan="EP1"
    az functionapp plan create --name $premium --resource-group $resourceGroupPremiumAppService --location "$location" --sku $skuPlan --max-burst 30 --min-instances 1 --is-linux true
}

function checkDirName() {
    dirName="${1}"
    if [[ -z "${dirName}" ]]; then
        bail "Must specify a folder name to deploy"
    fi
    if [[ ! -d "${dirName}" ]]; then
        bail "Folder ${dirName} doesn't exist"
    fi
}

function createFunction() {
    dirName="${1}"
    checkDirName "${dirName}"
    shortName=$(echo "${dirName}" | tr -d '_')

    # Create Storage account for this function
    az storage account create -n ${shortName} -g ${resourceGroup} -l ${location} --sku Standard_LRS
    
    # Create Azure Function within the specified App Service Plan
    if [[ "${dirName}" == "${pmc_scan_repos}" ]]; then
        premiumPlanId=$(az appservice plan show --name $premium --resource-group $resourceGroupPremiumAppService --query 'id' -o tsv)
        planParam=" --plan $premiumPlanId"
    else
        planParam=" --consumption-plan-location $location"
    fi
    az functionapp create -s ${shortName} -g ${resourceGroup} -n ${shortName} ${planParam} --functions-version 4 --os-type linux --runtime python --runtime-version 3.9

    # Configure storage account, which is present on all functions
    az functionapp config appsettings set --name $shortName --resource-group $resourceGroup --settings "pmcstatusprimary_CONNECTION=$primarystorage_connectionstring"

    # Configure settings specific to the "pmc_status_delivery" function
    if [[ "${dirName}" == "pmc_status_delivery" ]]; then
        az functionapp config appsettings set --name $functionApp --resource-group $resourceGroup --settings "JsonContainerName=dynamic-public-data"
        az functionapp config appsettings set --name $functionApp --resource-group $resourceGroup --settings "JsonBlobName=repository_status.json"
        az functionapp config appsettings set --name $functionApp --resource-group $resourceGroup --settings "ResultsQueueName=results-queue"
        az resource update --resource-type Microsoft.Web/sites -g $resourceGroup -n $functionApp/config/web --set properties.functionAppScaleLimit=1
    fi
}

function deployFunction() {
    # Deploy the Azure Function in the specified folder to its place in Azure
    dirName="${1}"
    checkDirName "${dirName}"
    shortName=$(echo "${dirName}" | tr -d '_')
    pushd "${dirName}" > /dev/null
    func azure functionapp publish ${shortName} --python --build remote
    popd > /dev/null
}

function createFunctions() {
    # Create the resources in which our function code will run
    for (( n=0; n<${#appPlans[@]}; n++ )); do
        createFunction ${dirNames[${n}]} ${appPlans[${n}]}
    done
}

function deployFunctions() {
    # Deploy function code to run in Azure
    for dirName in ${dirNames[@]}; do
        deployFunction ${dirName}
    done
}

createResourceGroups
createPrimaryStorage
primarystorage_connectionstring=$(az storage account show-connection-string --name $primarystorage --resource-group $resourceGroup --query "connectionString" -o tsv)
configurePrimaryStorage
createAppServicePlan
createFunctions
deployFunctions
