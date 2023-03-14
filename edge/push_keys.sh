#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

#### global variables
user="www-data"
signing_certs="microsoft.asc msopentech.asc"
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
    gpgdir="~/wwwgpg"
#### per-host actions
    copy_to_host $signing_certs
    do_on_host "rm -fr $gpgdir && install -m 700 -d $gpgdir"
    do_on_host gpg --homedir $gpgdir --import $signing_certs
    do_on_host "sudo rm -fr /var/pmc/wwwgpg && sudo mv $gpgdir /var/pmc/ && sudo chown -R www-data:www-data /var/pmc/wwwgpg"
    do_on_host rm $signing_certs
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
   echo "Usage: $0 target

target: a single mirror (e.g. wus1), a region code (e.g. euap),
        or 'all' signifying all mirrors in all regions
"
#### end usage documentation
    exit 1
}

#### controller-side prerequisite actions
for cert in $signing_certs; do
    if [ ! -f $cert ]; then
        curl --silent -o $cert https://packages.microsoft.com/keys/$cert
    fi
done
#### end controller-side prerequisite actions

#### arg parsing
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
