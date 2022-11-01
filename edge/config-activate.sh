#!/bin/bash
# Switch the active nginx configuration

goal="${1,,}"   # lowercase the argument
if [ "$goal" = "vnext" ]; then
    cp /etc/nginx/sites-available/vNext.conf /etc/nginx/sites-enabled/vNext.conf
    rm /etc/nginx/sites-enabled/vCurrent.conf
elif [ "$goal" = "vcurrent" ]; then
    cp /etc/nginx/sites-available/vCurrent.conf /etc/nginx/sites-enabled/vCurrent.conf
    rm /etc/nginx/sites-enabled/vNext.conf
else
    echo "Usage: $0 vnext|vcurrent"
    exit 1
fi
nginx -s reload
