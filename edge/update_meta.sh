#!/bin/bash
runfile=/var/run/lock/update_meta
pockets=/var/pmc/apt-repos.txt
force_flag=/var/pmc/force-update
max_jobs=4

function log {
    logger -p local3.info -t Fetch $@
}

function block_job_count_ge {
    count=$1
    while [ $(jobs -p | wc -l) -ge $count ]; do
        wait -n
    done
}

if [ -e $runfile ]; then
    pid=$(cat $runfile)
    if [ -e /proc/$pid ]; then
        log "Previous cron invocation still running - skip"
        exit 0      # Still running
    fi
fi
echo $$ > $runfile  # Our turn
log "Starting updates"

if [ -e "$pockets" ]; then
    opts="-z $pockets"
else
    opts=""
fi
curl -s -L -o $pockets $opts https://pmc-distro.trafficmanager.net/info/apt-repos.txt

if [ -f $force_flag ]; then
    force="--force"
else
    force=""
fi

for pocket in $(cat $pockets); do
    block_job_count_ge $max_jobs
    /usr/local/bin/fetch-apt-metadata $force $pocket &
done
block_job_count_ge 1

log "Completed updates"
rm -f $force_flag
rm $runfile
