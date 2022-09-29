#!/bin/bash -e
inputCsv="${1}"
isAME=False
function bail {
    >&2 echo ${@}
    exit 1
}

if  [[ -z "${inputCsv}" ]]; then
    bail "Must specify a csv filename"
elif [[ ! -f "${inputCsv}" ]]; then
    bail "File ${inputCsv} does not exist!"
fi

function newRandomOid() {
    # Generate a tempOid that we can replace when the publisher onboards
    partialOid=$[ $RANDOM % 8999 + 1000 ]
    now=$(date +%012s)
    echo "0000${partialOid}-0000-0000-0000-${now}"
}

failed=()
created=0
# Capture absolute path, since we have to change folders
inputCsvPath=$(realpath ${inputCsv})
pushd ../cli > /dev/null
cat ${inputCsvPath} | while read -r line; do
    username=$(echo ${line} | cut -d ',' -f 1) # Username
    oid=$(echo ${line} | cut -d ',' -f 2)      # Oid
    isAdmin=$(echo ${line} | cut -d ',' -f 3)  # isAdmin
    isProd=$(echo ${line} | cut -d ',' -f 4)   # isProd
    email=$(echo ${line} | cut -d ',' -f 5)    # email address
    icmSvc=$(echo ${line} | cut -d ',' -f 6)   # IcM Team
    icmTeam=$(echo ${line} | cut -d ',' -f 7)  # IcM Service
    if [[ "${isAME}" == "true" ]] || [[ ${#oid} != 36 ]] || ! newOid=$(az ad sp show --id ${oid} --query id --out tsv); then
        newOid=$(newRandomOid)
        enableOption="--disabled"
    else
        # Preserve existing account
        enableOption="--enabled"
    fi
    
    if [[ "${isAdmin}" == TRUE ]]; then
        roleOption=("--role" "Repo_Admin")
    else
        roleOption=("" "")
    fi
    echo "pmc account create ${enableOption} ${roleOption[@]} ${newOid} ${username} ${email} ${icmSvc} ${icmTeam}"
    if ! poetry run pmc account create ${enableOption} ${roleOption[@]} ${newOid} ${username} "${email}" ${icmSvc} "${icmTeam}"; then
        echo "FAILED to add ${username}:${oid}"
        failed+=("${username}:${oid}")
    else
        echo "Created account ${username}"
        created=$((created+1))
    fi
done
popd > /dev/null
echo "Created ${created} accounts with ${#failed[@]} failures"
for name in ${failed[@]}; do
    echo "FAILED account ${name}"
done