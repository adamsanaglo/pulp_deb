#!/bin/bash
runfile=/var/run/lock/update_meta
pockets=/var/pmc/apt-repos.txt
force_flag=/var/pmc/force-update
max_jobs=4
max_runtime=2700    # seconds

function log {
    logger -p local3.info -t Fetch $@
}

function block_job_count_ge {
    count=$1
    while [ $(jobs -p | wc -l) -ge $count ]; do
        wait -n
    done
}

function process_age {
    target=$1
    hz=$(getconf CLK_TCK)
    uptime=$(awk '{print int($1)}' /proc/uptime)
    start_delta=$(awk "{print int(\$22 / $hz)}" /proc/$target/stat)
    echo $((uptime - start_delta))
}

if [ -e $runfile ]; then
    pid=$(cat $runfile)
    if [ -n "$pid" -a -d /proc/$pid ]; then
        age=$(process_age $pid)
        if [ $age -le $max_runtime ]; then
            log "Previous invocation pid $pid age ${age}s - skip"
            exit 0      # Still running
        fi
        now=$(date +%s)
        then=$((now - age))
        datetime=$(date --iso-8601=seconds --date @$then)
        log "Previous invocation [pid $pid age ${age}s started at $datetime] hung; killing it"
        kill $target
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
