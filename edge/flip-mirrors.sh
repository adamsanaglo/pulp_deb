#!/bin/bash

function usage {
    echo "Usage:
$0 mode target

mode: one of vcurrent or vnext

target: a single mirror (e.g. wus1), a region code (e.g. euap),
       or 'all' signifying all mirrors in all regions"
    exit 1
}

sshopts="-o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

function switch_mirror {
    config=$1
    host=$2
    do_on_host sudo ./config-activate.sh $config
}

function switch_mirrors {
    config=$1
    region=$2

    for n in 1 2 3 4; do
        name=$region$n
        if grep -q $name /etc/hosts; then
            switch_mirror $config $name
        fi
    done
}

regions="euap wus eus sus neu weu eas sea"

mode=${1,,}
target=${2,,}

if [ "$mode" != "vnext" -a "$mode" != "vcurrent" ]; then
    echo "Unknown mode '$mode'"
    usage
fi

if [ -z "$target" ]; then
    usage
elseif [ "$target" == "all" ]; then
    for r in $regions; do
        switch_mirrors $mode $r
    done
elif grep -q $target <<<"$regions"; then
    switch_mirrors $mode $target
elif [[ "$target" =~ [[:alpha:]]*[[:digit:]] ]]; then
    switch_mirror $mode $target
else
    echo Unrecognized target $target
    usage
fi
