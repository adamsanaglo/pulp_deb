#!/bin/bash -e

function bail {
    >&2 echo ${@}
    exit 1
}

function set_initial_vars() {
    rg="${prefix}-rg"
    vnet="${prefix}-vnet"
    aks_subnet="${prefix}-aks-subnet"
    pg_subnet="${prefix}-pg-subnet"
    aks="${prefix}-kube-cluster"
    acr="$(echo $prefix | tr -cd '[:alnum:]')acr"  # alphanumeric only
    pg="${prefix}-pg"
}

function get_az_cli_vars() {
    export AZURE_TENANT_ID=$(az account show --query tenantId -o tsv | tr -d '\r')
    export CLIENT_ID=$(az aks show -g $rg -n $aks --query addonProfiles.azureKeyvaultSecretsProvider.identity.clientId -o tsv | tr -d '\r')
    export pg_server=$(az postgres flexible-server show -g $rg -n $pg --query 'fullyQualifiedDomainName' -o tsv | tr -d '\r')
    export loginserver=$(az acr show -g $rg --name $acr --query 'loginServer' -o tsv | tr -d '\r')
}

function get_aks_creds() {
    az aks get-credentials -g $rg --name $aks
}

function apply_kube_config() {
    envsubst < ${1} | kubectl apply -f -
}

function apply_migrations() {
    # run and wait for the db migrations
    apply_kube_config migration.yml
    kubectl wait --for=condition=complete --timeout=500s job/migration
    kubectl delete job/migration
}

function pmc_run() {
    if [[ -z "${PMCPOD}" ]]; then
        PMCPOD=$(kubectl get pod -l app=pmc -o jsonpath="{.items[0].metadata.name}")
    fi
    kubectl exec --stdin -c pmc --tty $PMCPOD -- /bin/bash -c ${@}
}

function initializePMCDB() {
    # Init pmc db and prep for pulp access
    psqlcmd="PGPASSWORD=$PMC_POSTGRES_PASSWORD psql -h $pg_server -U pmcserver"
    pmc_run "${psqlcmd} -d postgres -c 'create database pmcserver'"
    pmc_run "alembic upgrade head"
    pmc_run "${psqlcmd} -d pmcserver -c \"insert into account (id, oid, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited) values (gen_random_uuid(), '$account_id', 'dev', 'Account_Admin', 'dev', 'dev', 'dev@user.com', 't', now(), now())\""
    pmc_run "${psqlcmd} -d postgres -c \"create user pulp with encrypted password '$PULP_POSTGRES_PASSWORD'\""
    pmc_run "${psqlcmd} -d postgres -c 'create database pulp'"
    pmc_run "${psqlcmd} -d postgres -c 'grant all privileges on database pulp to pulp'"
}

function worker_run() {
    if [[ -z "${WORKERPOD}" ]]; then
        WORKERPOD=$(kubectl get pod -l app=pulp-worker -o jsonpath="{.items[0].metadata.name}")
    fi
    kubectl exec --stdin -c pulp-worker --tty $WORKERPOD -- /bin/bash -c ${@}
}

function register_signing_services () {
    worker_run "/usr/bin/add_signer.sh" "${1}" "${2}" "${3}"
}

function configureSigningServices() {
    declare -A legacyKey
    legacyKey["ppe"]="legacy_ppe.asc"
    legacyKey["tux"]="legacy_tux.asc"
    legacyKey["prod"]="msopentech.asc"

    # Register the "legacy" key that resides in the signing container
    register_signing_services "legacy" "/sign_cli/sign_legacy" "/sign_cli/${legacyKey[${environment}]}"
    if [[ "$prefix" =~ "ppe" ]]; then
        # In PPE-like environments, register the ESRP test scripts for test signing.
        register_signing_services "esrp" "/sign_cli/sign_esrp_test" "/sign_cli/prsslinuxtest.asc"
    else
        # In Prod / Tux-Dev-like environments, register the real ESRP scripts for real signing.
        register_signing_services "esrp" "/sign_cli/sign_esrp_prod" "/sign_cli/microsoft.asc"
    fi
}