#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

#### global variables
cacheRootDir="/mnt/cache"
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
    echo "Removing $cacheFilePath from $host"
#### per-host actions
    do_on_host sudo rm -f $cacheFilePath
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
   echo "Usage: $0 URL target

URL:    The path to a single file that needs to be purged from edge cache. Acceptable inputs:
        - http[s]://packages.microsoft.com/path/to/file
        - /path/to/file
target: A single mirror (e.g. wus1), a region code (e.g. euap),
        or 'all' signifying all mirrors in all regions
"
#### end usage documentation
    exit 1
}

#### arg parsing
url=$1
target=${2,,}
#### end arg parsing

if [ -z "$target" ]; then
    usage
fi

#### controller-side prerequisite actions

# Parse the URL param into a usable form
if [[ ${url} =~ ^https?://packages.microsoft.com/.+$ ]]; then
    # Nginx keys only use the URL path; strip the protocol and domain name
    urlPath=$(echo $url | sed -E 's|https?://packages.microsoft.com||g')
elif [[ ${url} =~ ^/.+$ ]]; then
    # Provided url is already in the correct format
    urlPath=$url
else
    echo "Provided URL parameter [$url] is invalid."
    usage
fi

# Calculate the md5sum and use that to find the path on disk
# Example: /mnt/cache/c/3e/adc648898177eb14ccf088305f05d3ec
# - First subfolder is last char in checksum
# - Second subfolder is 2 chars preceeding the last char
urlSum=$(echo -n $urlPath | md5sum | cut -d ' ' -f 1)
tmp=${urlSum: -3}
subFolder1=${tmp: -1}
subFolder2=${tmp:0:2}
cacheFilePath="$cacheRootDir/$subFolder1/$subFolder2/$urlSum"
echo "Correlated $urlPath to $cacheFilePath"
#### end controller-side prerequisite actions

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
