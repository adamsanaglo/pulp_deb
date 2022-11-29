#!/bin/bash

check_idle() {
    local __ret=$1
    curl --silent localhost:8888/status | grep --silent "idle"
    eval $__ret=$?
}

wait_for_idle () {
    check_idle idle
    while [ $idle -ne 0 ]; do
        echo "Waiting for signing tasks to complete."
        sleep 10
        check_idle idle
    done
}

# When Docker / AKS wants to shut the container down they send a SIGTERM to the entrypoint process.
# Wait for the signing processes to complete, and then propagate it to uvicorn.
# https://linuxconfig.org/how-to-propagate-a-signal-to-child-processes-from-a-bash-script
trap 'wait_for_idle; kill "${uvicorn_pid}"; wait "${uvicorn_pid}"' SIGINT SIGTERM

/usr/bin/redis-server &
/usr/bin/uvicorn --workers 4 --host 0.0.0.0 --port 8888 main:app 2>&1 &

uvicorn_pid="$!"
wait "${uvicorn_pid}"