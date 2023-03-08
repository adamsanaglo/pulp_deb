#!/bin/bash
# Restart nginx after logging an appropriate message to syslog

function log {
    severity="$1"
    shift
    /usr/bin/logger -p local3.$severity -t PMCnginx $@
}

log err Restarting nginx after multiple failures
systemctl reset-failed nginx
systemctl restart nginx
