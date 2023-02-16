#!/bin/bash -e

function bail {
    >&2 echo ${@}
    exit 1
}

function set_initial_vars() {
    environment="${1}"
    if [[ -z "${environment}" ]]; then
        bail "Must specify environment (ppe|tux|prod)"
    elif [[ "${environment}" == "tux" ]]; then
        bail "Environment '${environment}' uses ExpressRoute, which is incompatible with AKS."
    elif [[ "${environment}" == "ppe" ]] || [[ "${environment}" == "prod" ]]; then
        . ./${environment}.sh
    else
        bail "Environment '${environment}' not supported"
    fi
    rg="${prefix}-rg"
    vnet="${prefix}-vnet"
    aks_subnet="${prefix}-aks-subnet"
    pg_subnet="${prefix}-pg-subnet"
    export kv="${prefix}-keyvault"
    aks="${prefix}-kube-cluster"
    acr="$(echo $prefix | tr -cd '[:alnum:]')acr"  # alphanumeric only
    pg="${prefix}-pg"
    storageprefix=$(echo $prefix | tr -d '[:punct:]') # Storage account names can't include punctuation
    export pg_size="Standard_D2s_v3"
    export bstg="${storageprefix}blobstorage"
    export lstg="${storageprefix}logstorage"
    export esrpAuthCertPath="/mnt/secrets/${esrpAuthCert}"
    export api_cert_name="api-cert"  # name of the tls certificate in the keyvault
    export content_cert_name="content-cert"
    export min_pulp_workers="2"
    export min_pulp_content="2"
    env_overrides
}

function get_az_cli_vars() {
    export AZURE_TENANT_ID=$(az account show --query tenantId -o tsv | tr -d '\r')
    export CLIENT_ID=$(az aks show -g $rg -n $aks --query addonProfiles.azureKeyvaultSecretsProvider.identity.clientId -o tsv | tr -d '\r')
    export pg_server=$(az postgres flexible-server show -g $rg -n $pg --query 'fullyQualifiedDomainName' -o tsv | tr -d '\r')
    export loginserver=$(az acr show -g $rg --name $acr --query 'loginServer' -o tsv | tr -d '\r')
}

function get_blob_storage_key() {
    az storage account keys list -n $bstg -g $rg --query "[? keyName == '${1}'].value" --out tsv | tr -d '\r'
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

function get_pod_name() {
    if [ $# -ne 1 ]; then
        echo 'Usage: get_pod_name <container_name>'
        return
    fi
    declare -A pods
    for name in pmc pulp-worker pulp-content nginx-api nginx-content; do
        pods["${name}"]="${name}"
    done
    pods["signer"]="pulp-worker"
    pods["pulp-api"]="pmc"
    local POD=${pods[${1}]}
    if [[ -z "${POD}" ]]; then
        echo "Container name ${1} not recognized"
        return
    fi
    kubectl get pods -l app=${POD} -o jsonpath='{.items[0].metadata.name}'
}

function get_service_ip() {
    if [ $# -ne 1 ]; then
        echo 'Usage: get_service_ip <service_name>'
        return
    fi
    kubectl get service/${1} -o jsonpath="{.status.loadBalancer.ingress[0].ip}"
}

function kube_init() {
    # Set the necessary variables for running kubectl commands.
    if [ $# -ne 1 ]; then
        echo 'Usage: kube_init <environment>'
        return
    fi
    if [ "$1" = "prod" ]; then
        ../tools/login-deploy.py
    fi
    set_initial_vars $1
    get_az_cli_vars
    get_aks_creds
}

function kube_bash() {
    # Starts a bash shell in the specified container.
    if [ $# -lt 1 ]; then
        echo 'Usage: kube_bash <container_name> [<command> ...]'
        return
    fi

    local container="${1}"
    shift
    local podName=$(get_pod_name ${container})
    if [ $# -lt 1 ]; then
        kubectl exec -it -c ${container} $podName -- /bin/bash
    else
        kubectl exec -it -c ${container} $podName -- /bin/bash -c "$*"
    fi
}

function kube_db() {
    # Starts a db shell, tunneling thorugh the pmc container
    if [ $# -lt 1 ]; then
        echo 'Usage: kube_db <db_name> [<query> ...]'
        return
    fi

    local db_name="$1"
    shift
    if [ "$db_name" = "pmcserver" ]; then
        local secret='$SECRETS_MOUNTPOINT/pmcPostgresPassword'
    elif [ "$db_name" = "pulp" ]; then
        local secret='$SECRETS_MOUNTPOINT/pulpPostgresPassword'
    else
        echo "db_name must be pmcserver or pulp"
        return
    fi

    if [ $# -lt 1 ]; then
        kube_bash 'pmc' "PGPASSWORD=\$(cat ${secret}) psql -U $db_name -d $db_name -h \${POSTGRES_SERVER}"
    else
        kube_bash 'pmc' "PGPASSWORD=\$(cat ${secret}) psql -U $db_name -d $db_name -h \${POSTGRES_SERVER} -c '$*'"
    fi
}

function kube_pulp_shell() {
    # Starts a pulp shell in the pulp-api container
    # Usage: kube_pulp_shell
    kube_bash 'pulp-api' 'source /usr/bin/pmc-secrets-exporter.sh; pulpcore-manager shell'
}

function create_initial_account() {
    # Add the initial Account_Admin specified in the env-specific setup script.
    kube_db 'pmcserver' "insert into account (id, oid, name, role, icm_service, icm_team, contact_email, is_enabled, created_at, last_edited) values (gen_random_uuid(), '$account_id', 'dev', 'Account_Admin', 'dev', 'dev', 'dev@user.com', 't', now(), now())"
}

function register_signing_services () {
    if [ $# -ne 3 ]; then
        echo 'Usage: register_signing_services <script_type> <script_path> <public_key>'
        return
    fi
    kube_bash 'pulp-worker' "/usr/bin/add_signer.sh ${1} ${2} ${3}"
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
