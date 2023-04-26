#!/bin/bash
action=$1

syslog=/var/log/syslog
access=/var/log/nginx/access.log
error=/var/log/nginx/error.log

function usage {
    echo "usage: $0 404|access|dist|error|fetch" 1>&2
    exit 1
}

if [[ -z "$action" ]]; then
    usage
fi

case $action in
404   ) sudo tail -f $access | fgrep " 404 " | egrep -v "/(i18n|clamav)/" | fgrep -v /Packages\.bz2 ;;
access) sudo tail -f $access ;;
dist  ) sudo tail -f $access | fgrep /dists/ | fgrep -v /i18n/ | egrep -v " (200|206|304) " | fgrep -v /Packages\.bz2  ;;
error ) sudo tail -f $error ;;
fetch ) sudo tail -f $syslog | grep Fetch: ;;
*     ) usage ;;
esac
