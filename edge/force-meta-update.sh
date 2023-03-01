#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

user="www-data"

sshopts="-o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

function act_on_host {
    host=$1

    do_on_host sudo touch /var/pmc/force-update
}

function act_on_region {
    region=$1

    for n in 1 2 3 4; do
        name=$region$n
        if grep -q $name /etc/hosts; then
            act_on_host $name
        fi
    done
}

regions="euap wus eus sus neu weu eas sea"

function usage {
    echo "Usage: $0 target

target: a single mirror (e.g. wus1), a region code (e.g. euap),
        or 'all' signifying all mirrors in all regions"
    exit 1
}

target=${1,,}

if [ -z "$target" ]; then
    usage
elif [ "$target" == "all" ]; then
    for r in $regions; do
        act_on_region $r
    done
elif grep -q $target <<<"$regions"; then
    act_on_region $target
elif [[ "$target" =~ [[:alpha:]]*[[:digit:]] ]]; then
    act_on_host $target
else
    echo Unrecognized target $target
    usage
fi
