#!/usr/bin/env python
# A helper script to do a 1-time migration of packages.microsoft.com remotes to
# azure-apt-cat.cloudapp.net.

import json
import subprocess
import sys

GOOD = "azure-apt-cat.cloudapp.net"
BAD = "packages.microsoft.com"

try:
    command = sys.argv[1]
except IndexError:
    print("Usage: ./fix-remote-upstream.py --test|--run")
    exit()


result = subprocess.run(["pmc", "remote", "list", "--limit", "9001"], capture_output=True)
remotes = json.loads(result.stdout)["results"]

broken = [x for x in remotes if BAD in x["url"]]
if not broken:
    print("Nothing to fix!")
    exit()

for remote in broken:
    new_url = remote["url"].replace(BAD, GOOD)
    print(f"Setting url for {remote['name']} to {new_url}.")
    if command == "--run":
        subprocess.run(["pmc", "remote", "update", remote["id"], "--url", new_url])
