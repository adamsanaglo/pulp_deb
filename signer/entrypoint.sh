#!/bin/bash

/usr/bin/redis-server &
/usr/bin/uvicorn --workers 4 --host 0.0.0.0 --port 8888 main:app 2>&1
