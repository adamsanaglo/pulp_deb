#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

user="www-data"
do_prereqs="no"

sshopts="-o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

function act_on_host {
    host=$1
    systemd_dropins="restart.conf override.conf"
    varpmc_scripts="update_meta.sh restart-nginx.sh"
    local_scripts="config-activate.sh watch.sh"
    other_files="fetch-apt-metadata.py crontab pmc-restart.service"

    if [ $do_prereqs = "yes" ]; then
        do_on_host sudo install -o $user -g $user -m 755 -d /var/pmc /var/pmc/www
        do_on_host sudo apt-get install -y python3-pip python3-requests
        # For some reason (probably umask related) installing python modules in
        # this manner, via ssh and sudo -H, leaves them inaccessible by non-root.
        # The chmod commands brute-force restoration of correct permissions.
        do_on_host sudo -H pip3 install typer python-dateutil
        do_on_host "sudo find /usr/local/lib/python3.6/dist-packages -type d | xargs sudo chmod o+rx"
        do_on_host "sudo find /usr/local/lib/python3.6/dist-packages -type f | xargs sudo chmod o+r"
    fi
    copy_to_host $systemd_dropins $varpmc_scripts $local_scripts $other_files
    do_on_host sudo install -o $user -g $user -m 755 -t /var/pmc $varpmc_scripts
    do_on_host sudo install -o root -g root -m 555 ~/fetch-apt-metadata.py /usr/local/bin/fetch-apt-metadata
    do_on_host sudo install -o root -g root -m 644 ~/crontab /etc/cron.d/update_meta
    do_on_host sudo install -o root -g root -m 755 -d /etc/systemd/system/nginx.service.d
    do_on_host sudo install -o root -g root -m 644 -t /etc/systemd/system/nginx.service.d $systemd_dropins
    do_on_host sudo install -o root -g root -m 644 -t /etc/systemd/system pmc-restart.service
    do_on_host sudo systemctl daemon-reload
    do_on_host rm $systemd_dropins $varpmc_scripts $other_files
    do_on_host chmod 755 $local_scripts     # ...and leave them here
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
    echo "Usage: $0 [--prereqs] target

target: a single mirror (e.g. wus1), a region code (e.g. euap),
        or 'all' signifying all mirrors in all regions

--prereqs: install required directories, packages, etc"
    exit 1
}

if [ "$1" = "--prereqs" ]; then
    do_prereqs="yes"
    shift
fi

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
