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

failedRemotes=()
failedRepos=()
failedDistros=()
remoteCount=0
repoCount=0
distroCount=0
# Capture absolute path, since we have to change folders
inputCsvPath=$(realpath ${inputCsv})
pushd ../cli > /dev/null
# Get a list of unique repo IDs; parse releases/dists separately
cat ${inputCsvPath} | while read -r line | cut -d ',' -f 1,2,4 | sort -u); do
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
    if ! remote_id=$(poetry run pmc --id-only remote create ${distOption[@]} ${archOption[@]} ${url}-${type} ${type} ${remote_url}); then
        echo "Failed to add Remote ${url}-${type}. Continue..."
        failedRemotes+=("${url}-${type}")
        continue
    fi
    remoteCount=$((remoteCount+1))
    echo "Created remote ${url}-${type} ${remote_id} [${remoteCount}]"

    # 2. Create Repo
    if ! repo_id=$(poetry run pmc --id-only repo create --remote ${remote_id} --signing-service ${signers[${prss}]} ${url}-${type} ${type});  then
        echo "Failed to add Repo ${url}-${type}. Continue..."
        failedRepos+=("${url}-${type}")
        continue
    fi
    repoCount=$((repoCount+1))
    echo "Created repo ${url}-${type} ${repo_id} [${repoCount}]"

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
    if ! poetry run pmc distro create ${url}-${type} ${type} ${basePath} --repository ${repo_id}; then
        echo "Failed to add Distro ${url}-${type}. Continue..."
        failedDistros+=("${url}-${type}")
        continue
    fi
    distroCount=$((distroCount+1))
    echo "Created distro ${url}-${type} [${distroCount}]"
done

echo "Created ${remoteCount} remotes with ${#failedRemotes[@]} failures"
echo "Created ${repoCount} repos with ${#failedRepos[@]} failures"
echo "Created ${distroCount} distros with ${#failedDistros[@]} failures"
for name in ${failedRemotes[@]}; do
    echo "FAILED remote ${name}"
done
for name in ${failedRepos[@]}; do
    echo "FAILED repo ${name}"
done
for name in ${failedDistros[@]}; do
    echo "FAILED distro ${name}"
done