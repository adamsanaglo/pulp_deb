#!/bin/bash -e
# Assumes you're deploying from apt_automation@jumpbox

#### global variables
user="www-data"
certDest="/etc/ssl/certs/pmc-ssl.cer"
keyDest="/etc/ssl/private/pmc-ssl.key"
#### end global variables

sshopts="-q -o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

function act_on_host {
    host=$1
#### per-host actions
    # Copy to host
    copy_to_host $cert_path $key_path

    # Install
    do_on_host "sudo install -o root -g root -m 600 ~/${key_filename} ${keyDest} && sudo install -o root -g root -m 644 ~/${cert_filename} ${certDest} && sudo nginx -s reload && shred -uz ${key_filename} ${cert_filename}"

    # Validate
    do_on_host "curl --silent --resolve ${dnsname}:443:127.0.0.1 -H 'Host: ${dnsname}' https://${dnsname}/ | grep Welcome"
    echo -n | openssl s_client -servername ${dnsname} -connect ${host}:443 2>/dev/null | openssl x509 -noout -enddate
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
   echo "Usage: $0 certificate private_key target

certificate: Path to a TLS certificate file
private_key: Path to a TLS private key
target:      a single mirror (e.g. wus1), a region code (e.g. euap),
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
cert_path="${1}"
key_path="${2}"
target=${3,,}
#### end arg parsing

if [ -z "$target" ]; then
    usage
elif [[ ! -f "${cert_path}" ]]; then
    echo "File ${cert_path} doesn't exist"
    usage
elif [[ ! -f "${key_path}" ]]; then
    echo "File ${key_path} doesn't exist"
    usage
fi
cert_filename=$(basename ${cert_path})
key_filename=$(basename ${key_path})
dnsname=$(openssl x509 -noout -subject -in ${cert_path} | awk '{print $NF}')
if [ "$target" == "all" ]; then
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
