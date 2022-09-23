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

# Capture absolute path, since we have to change folders
inputCsvPath=$(realpath ${inputCsv})
pushd ../cli > /dev/null
IFS=$'\n'
for line in $(cat ${inputCsvPath}); do
    username=$(echo ${line} | cut -d ',' -f 1) # Username
    oid=$(echo ${line} | cut -d ',' -f 2)      # Oid
    isAdmin=$(echo ${line} | cut -d ',' -f 3)  # isAdmin
    isProd=$(echo ${line} | cut -d ',' -f 4)   # isProd
    email=$(echo ${line} | cut -d ',' -f 5)    # email address
    icmSvc=$(echo ${line} | cut -d ',' -f 6)   # IcM Team
    icmTeam=$(echo ${line} | cut -d ',' -f 7)  # IcM Service
    if [[ "${isAME}" == "true" ]] || [[ ${#oid} != 36 ]]; then
        # Generate a tempOid that we can replace when the publisher onboards
        partialOid=$[ $RANDOM % 8999 + 1000 ]
        oid="00000000-0000-0000-0000-00000000${partialOid}"
        enableOption="--disabled"
    else
        # Preserve existing oid
        enableOption="--enabled"
    fi
    
    if [[ "${isAdmin}" == TRUE ]]; then
        roleOption=("--role" "Repo_Admin")
    else
        roleOption=("" "")
    fi
    echo "pmc account create --disabled ${roleOption[@]} ${oid} ${username} ${email} ${icmSvc} ${icmTeam}"
    poetry run pmc account create --disabled ${roleOption[@]} ${oid} ${username} "${email}" ${icmSvc} "${icmTeam}"
    echo "Created account ${username}"
done
popd > /dev/null