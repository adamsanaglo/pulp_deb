#!/bin/bash

function usage {
    echo "Usage:
$0 mode path target

mode: the config to be updated (vcurrent, vnext)

path: filesystem path to the config to be pushed

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

function push_config {
    config=$1
    localpath=$2
    host=$3
    basename=$(basename $localpath)
    if [ $config == "vnext" ]; then
        targetname="vNext.conf"
    else
        targetname="vCurrent.conf"
    fi
    copy_to_host $localpath
    do_on_host sudo install -o root -g root -m 644 $basename /etc/nginx/sites-available/$targetname
}

function push_configs {
    config=$1
    localpath=$2
    region=$3

    for n in 1 2 3 4; do
        name=$region$n
        if grep -q $name /etc/hosts; then
            push_config $config $localpath $name
        fi
    done
}

regions="euap wus eus sus neu weu eas sea"

mode=${1,,}
path=$2
target=${3,,}

if [ "$mode" != "vnext" -a "$mode" != "vcurrent" ]; then
    echo "Unknown mode '$mode'"
    usage
fi

if [ ! -e $path ]; then
    echo "No such file '$path'"
    usage
fi

if [ -z "$target" ]; then
    usage
elif [ "$target" == "all" ]; then
    for r in $regions; do
        push_configs $mode $path $r
    done
elif grep -q $target <<<"$regions"; then
    push_configs $mode $path $target
elif [[ "$target" =~ [[:alpha:]]*[[:digit:]] ]]; then
    push_config $mode $path $target
else
    echo Unrecognized target $target
    usage
fi

sha256sum $path
