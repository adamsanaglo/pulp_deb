#!/bin/bash -e
inputCsv="${1}"
function bail {
    >&2 echo ${@}
    exit 1
}
urlPrefix="http://csd.packages.ppe.trafficmanager.net"
declare -A repos
repos["apt"]="repos"
repos["yum"]="yumrepos"

declare -A signers
signers["True"]="esrp"
signers["False"]="legacy"

declare -A paths
paths["apt"]="repos"
paths["yum"]="yumrepos"

if  [[ -z "${inputCsv}" ]]; then
    bail "Must specify a csv filename"
elif [[ ! -f "${inputCsv}" ]]; then
    bail "File ${inputCsv} does not exist!"
fi

# Capture absolute path, since we have to change folders
inputCsvPath=$(realpath ${inputCsv})
pushd ../cli > /dev/null
IFS=$'\n'
# Get a list of unique repo IDs; parse releases/dists separately
for line in $(cat ${inputCsvPath} | cut -d ',' -f 1,2,4 | sort -u); do
    type=$(echo ${line} | cut -d ',' -f 1)     # Type (apt|yum)
    url=$(echo ${line} | cut -d ',' -f 2)      # Url
    prss=$(echo ${line} | cut -d ',' -f 3)     # Prss
    remote_url="${urlPrefix}/${repos[${type}]}/${url}"
    if [[ "${type}" == "apt" ]]; then
        # Get all dists for this repo, trim trailing semi-colon
        dists=$(grep "^apt,${url}," ${inputCsvPath}  | cut -d ',' -f 3 | tr '\n' ';' | sed 's/;$//g')
        distOption=("--distributions" "${dists}")
        archOption=("--architectures" "amd64;arm64;armhf")
    else
        distOption=()
        archOption=()
    fi

    # 1. Create Remote
    remote_id=$(poetry run pmc --id-only remote create ${distOption[@]} ${archOption[@]} ${url}-${type} ${type} ${remote_url})
    echo "Created remote ${url}-${type} ${remote_id}"

    # 2. Create Repo
    repo_id=$(poetry run pmc --id-only repo create --remote ${remote_id} --signing-service ${signers[${prss}]} ${url}-${type} ${type})
    echo "Created repo ${url}-${type} ${repo_id}"

    # 3. Create Releases
    if [[ "${type}" == "apt" ]]; then
        for release in $(grep "^apt,${url}," ${inputCsvPath}  | cut -d ',' -f 3); do
            # This seems to get timeouts but succeeds anyway
            ! poetry run pmc repo releases create ${repo_id} ${release} ${release} ${release} 2> /dev/null
            echo "Created release ${url}-${type} ${release}"
        done
    fi

    #4 Create Distribution
    basePath="${paths[${type}]}/${url}"
    poetry run pmc distro create ${url}-${type} ${type} ${basePath} --repository ${repo_id}
    echo "Created distro ${url}-${type}"
done
