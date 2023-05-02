#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

#### global variables
user="www-data"
pockets="/var/pmc/apt-repos.txt"
local_file="apt-repos.txt"
force="no"
#### end global variables

sshopts="-o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

function act_on_host {
    host=$1
#### per-host actions
    size=$(do_on_host "sudo cat $pockets | wc -l")
    if [[ $force = "yes" || $size -lt 400 ]]; then
	copy_to_host $local_file
	do_on_host sudo install -o $user -g $user -m 0664 $local_file $pockets
	do_on_host rm $local_file
	echo "Updated $pockets on $host - was $size lines"
    fi
#### end per-host actions
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
#### usage documentation
   echo "Push the latest apt pocket file to edge servers with bad copies.
   
Usage: $0 [--force] target

target: a single mirror (e.g. wus1), a region code (e.g. euap),
        or 'all' signifying all mirrors in all regions

If --force is specified, the pocket file is pushed even if the copy
on the server seems okay.
"
#### end usage documentation
    exit 1
}

#### controller-side prerequisite actions
curl -L -o $local_file https://pmc-distro.trafficmanager.net/info/apt-repos.txt
#### end controller-side prerequisite actions

#### arg parsing
if [[ "$1" = "--force" ]]; then
    force="yes"
    shift
fi
target=${1,,}
#### end arg parsing

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
