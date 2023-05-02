#!/bin/bash
runfile=/var/run/lock/update_meta
pockets=/var/pmc/apt-repos.txt
force_flag=/var/pmc/force-update
max_jobs=4
max_runtime=2700    # seconds

function log {
    logger -p local3.info -t Fetch $@
}

# Block while there are $1 or more jobs running
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

if [ -f $force_flag ]; then
    force="--force"
    log "Starting updates (forced)"
else
    force=""
    log "Starting updates"
fi

min_size=$((9 * $(cat $pockets | wc -l) / 10))  # Shell only does integer math
cp $pockets $pockets.old

# Try to fetch apt-repos.txt 5 times with 5 second delay between retries
# The -z option means "GET IF_MODIFIED_SINCE" and will succeed with no action if
# the file hasn't changed since the last fetch
for i in {1..5}; do
    curl --fail -s -L -o $pockets -z $pockets https://pmc-distro.trafficmanager.net/info/apt-repos.txt
    status_code=$?
    if [ $status_code -eq 0 -o $i -eq 5 ]; then
        break
    fi
    log "Failed to fetch apt-repos.txt (curl status $status_code) - retrying in 5 seconds"
    sleep 5
done
if [ $status_code -ne 0 ]; then
    log "Complete failure to fetch apt-repos.txt (last curl status $status_code) - giving up"
    # Let the next cron job invocation try again
    rm $runfile 
    exit 1
fi

# We fetched *something*, make sure it's not obviously bogus
new_size=$(cat $pockets | wc -l)
if [[ $new_size -lt $min_size ]]; then
    log "New apt-repos.txt shrank by more than 10% ($new_size < $min_size)"
    mv $pockets.old $pockets    # Restore old version
    # Let the next cron job invocation try again
    rm $runfile
    exit 1
fi

chmod 644 $pockets
for pocket in $(cat $pockets); do
    block_job_count_ge $max_jobs
    /usr/local/bin/fetch-apt-metadata $force $pocket &
done
block_job_count_ge 1

log "Completed updates"
if [ -n "$force" ]; then
    rm -f $force_flag
fi
rm $runfile
