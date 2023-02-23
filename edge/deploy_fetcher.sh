#!/bin/bash
# Assumes you're deploying from apt_automation@jumpbox

user="www-data"

sshopts="-o StrictHostKeyChecking=no -i ~/.ssh/apt_automation.pem"
function do_on_host {
    ssh $sshopts apt-automation@$host "$@"
}
function copy_to_host {
    scp $sshopts $@ apt-automation@${host}:~
}

for host in $(cat ~/mirrors); do
    do_on_host sudo install -o $user -g $user -m 755 -d /var/pmc /var/pmc/www
    do_on_host sudo apt-get install -y python3-pip python3-requests
    do_on_host sudo -H pip3 install typer python-dateutil
    copy_to_host update_meta.sh fetch-apt-metadata.py crontab
    do_on_host sudo install -o $user -g $user -m 755 update_meta.sh /var/pmc
    do_on_host sudo install -o root -g root -m 555 ~/fetch-apt-metadata.py /usr/local/bin/fetch-apt-metadata
    do_on_host sudo install -o root -g root -m 644 ~/crontab /etc/cron.d/update_meta
done
