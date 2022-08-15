#!/bin/bash -e
# Creates the resources used by the status monitor, and deploys
# the Azure Function code to run in Azure.

resourceGroup=statusmonitor
location=centralus
storageAccount=pmcstatus
consumption=consumption # Low-cost Azure Function offering
premium=premium         # Upper tier Azure Function offering
appPlans=(${consumption} ${premium} ${consumption})
dirNames=("pmc_scan_mirrors" "pmc_scan_repos" "pmc_status_delivery")

function bail() {
    >&2 echo "${@}"
    exit 1
}

function createPrimaryStorage() {
    # Create Primary Storage Account that will host our website
    az storage account create -n ${storageAccount} -g ${resourceGroup} -l ${location} --sku Standard_LRS
    pushd website/ > /dev/null
    az storage blob upload-batch -s site-content/ -d '$web' --account-name ${storageAccount} --overwrite --auth-mode key
    popd > /dev/null
    az storage blob service-properties update --account-name ${storageAccount} --static-website --404-document 404.html --index-document mirror.html --auth-mode login
}

function createAppServicePlans() {
    # Create app service plans that will host our Azure Functions
    az appservice plan create -g ${resourceGroup} --is-linux -n ${consumption} -l ${location}
    az appservice plan create -g ${resourceGroup} --is-linux -n ${premium} --sku P1v2 -l ${location}
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
    appPlan=${2}

    # Create Storage account for this function
    az storage account create -n ${shortName} -g ${resourceGroup} -l ${location} --sku Standard_LRS
    
    # Create Azure Function within the specified App Service Plan
    az functionapp create -s ${shortName} -g ${resourceGroup} -p ${appPlan} -n ${shortName} --os-type linux --runtime python
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

createPrimaryStorage
createAppServicePlans
createFunctions
deployFunctions
