#!/bin/bash
runfile=/var/run/update_meta
pockets=/var/pmc/apt-repos.txt
max_jobs=4

function log {
    logger -p local3.info -t Fetch $@
}

if [ -e $runfile ]; then
    pid=$(cat /var/run/update_meta)
    if [ -e /proc/$pid ]; then
        log "Previous cron invocation still running - skip"
        exit 0      # Still running
    fi
fi
echo $$ | sudo tee $runfile >/dev/null    # Our turn
log "Starting updates"

if [ -e "$pockets" ]; then
    opts="-z $pockets"
else
    opts=""
fi
curl -s -L -o $pockets $opts https://pmc-distro.trafficmanager.net/info/apt-repos.txt

for pocket in $(cat $pockets); do
    if [ $(jobs | wc -l) -ge $max_jobs ]; then
        wait -n
    fi
    /usr/local/bin/fetch-apt-metadata $pocket &
done
wait

log "Completed updates"
sudo rm $runfile
