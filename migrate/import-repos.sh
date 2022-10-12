#!/bin/bash -e
inputCsv="${1}"
function bail {
    >&2 echo ${@}
    exit 1
}
urlPrefix="http://tux-devrepo.corp.microsoft.com"
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
failedPermission=()
remoteCount=0
repoCount=0
distroCount=0
permissionCount=0
# Capture absolute path, since we have to change folders
inputCsvPath=$(realpath ${inputCsv})
pushd ../cli > /dev/null
# Get a list of unique repo IDs; parse releases/dists separately
cat ${inputCsvPath} | cut -d ',' -f 1,2,4 | sort -u | while read -r line; do
    type=$(echo ${line} | cut -d ',' -f 1)     # Type (apt|yum)
    url=$(echo ${line} | cut -d ',' -f 2)      # Url
    prss=$(echo ${line} | cut -d ',' -f 3)     # Prss
    remote_url="${urlPrefix}/${repos[${type}]}/${url}"
    accounts=$(grep "^${type},${url}," ${inputCsvPath} | head -n 1 | cut -d ',' -f 5)
    repo_name="${url}-${type}"
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
    if ! remote_id=$(poetry run pmc --id-only remote create ${distOption[@]} ${archOption[@]} ${repo_name} ${type} ${remote_url}); then
        echo "Failed to add Remote ${repo_name}. Continue..."
        failedRemotes+=("${repo_name}")
        continue
    fi
    remoteCount=$((remoteCount+1))
    echo "Created remote ${repo_name} ${remote_id} [${remoteCount}]"

    # 2. Create Repo
    if ! repo_id=$(poetry run pmc --id-only repo create --remote ${remote_id} --signing-service ${signers[${prss}]} ${repo_name} ${type});  then
        echo "Failed to add Repo ${repo_name}. Continue..."
        failedRepos+=("${repo_name}")
        continue
    fi
    repoCount=$((repoCount+1))
    echo "Created repo ${repo_name} ${repo_id} [${repoCount}]"

    # 3. Assign Permissions
    # Parse accounts one-at-a-time, so that missing accounts do not block progress
    for account in $(echo "azlinux;dotnet;dotnet-release" | tr ';' ' '); do
        ! poetry run pmc -c /home/mbearup/.config/pmc/accountadmin.toml access repo grant ${account} "^${repo_name}\$" &> /dev/null
    done
    echo "Granted permission to ${repo_name}"

    # 4. Create Releases
    if [[ "${type}" == "apt" ]]; then
        for release in $(grep "^apt,${url}," ${inputCsvPath}  | cut -d ',' -f 3); do
            # This seems to get timeouts but succeeds anyway
            ! poetry run pmc repo releases create ${repo_id} ${release} ${release} ${release} 2> /dev/null
            echo "Created release ${repo_name} ${release}"
        done
    fi

    # 5. Create Distribution
    basePath="${paths[${type}]}/${url}"
    if ! poetry run pmc distro create ${repo_name} ${type} ${basePath} --repository ${repo_id}; then
        echo "Failed to add Distro ${repo_name}. Continue..."
        failedDistros+=("${repo_name}")
        continue
    fi
    distroCount=$((distroCount+1))
    echo "Created distro ${repo_name} [${distroCount}]"
done

echo "Created ${remoteCount} remotes with ${#failedRemotes[@]} failures"
echo "Created ${repoCount} repos with ${#failedRepos[@]} failures"
echo "Created ${distroCount} distros with ${#failedDistros[@]} failures"
echo "Created ${permissionCount} permissions with ${#failedPermission[@]} failures"
for name in ${failedRemotes[@]}; do
    echo "FAILED remote ${name}"
done
for name in ${failedRepos[@]}; do
    echo "FAILED repo ${name}"
done
for name in ${failedDistros[@]}; do
    echo "FAILED distro ${name}"
done
for name in ${failedPermission[@]}; do
    echo "FAILED permission ${name}"
done