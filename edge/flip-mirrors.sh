#!/bin/bash

function usage {
    echo "Usage:
$0 mode checksum target

mode: one of vcurrent or vnext
checksum: the sha256sum of the config file expected to be activated
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
    chk=$2
    host=$3
    do_on_host sudo ./config-activate.sh $config $chk
}

function switch_mirrors {
    config=$1
    chk=$2
    region=$3

    for n in 1 2 3 4; do
        name=$region$n
        if grep -q $name /etc/hosts; then
            switch_mirror $config $chk $name
        fi
    done
}

regions="euap wus eus sus neu weu eas sea"

mode=${1,,}
checksum=$2
target=${3,,}

if [ "$mode" != "vnext" -a "$mode" != "vcurrent" ]; then
    echo "Unknown mode '$mode'"
    usage
fi

if [ -z "$checksum" ]; then
    usage
fi

if [ -z "$target" ]; then
    usage
elif [ "$target" == "all" ]; then
    for r in $regions; do
        switch_mirrors $mode $checksum $r
    done
elif grep -q $target <<<"$regions"; then
    switch_mirrors $mode $checksum $target
elif [[ "$target" =~ [[:alpha:]]*[[:digit:]] ]]; then
    switch_mirror $mode $checksum $target
else
    echo Unrecognized target $target
    usage
fi
