#!/usr/bin/env python
# A helper script in case we need to wipe / recreate all deb or rpm repos.

import json
import subprocess
import sys
from typing import Dict, List

if len(sys.argv) < 2 or sys.argv[1] not in ("deb", "rpm"):
    print("Usage: delete-repos.py <deb|rpm> [--for-real]")
    exit()

FILTER = sys.argv[1]

DRY_RUN = True
if len(sys.argv) >= 3 and sys.argv[2] == "--for-real":
    DRY_RUN = False

KEYS = ["remotes", "distros", "repos"]


def unpaginate_and_filter_list(type: str):
    ret: List[str] = []
    offset = 0
    more = True
    while more:
        results = subprocess.run(
            ["poetry", "run", "pmc", type, "list", "--offset", str(offset)],
            capture_output=True,
        )
        obj = json.loads(results.stdout)
        ret.extend([x["id"] for x in obj["results"] if FILTER in x["id"]])
        offset += 100
        more = offset < obj["count"]

    return ret


for key in KEYS:
    items = unpaginate_and_filter_list(key)
    print(f"Deleting {key}:")
    for item in items:
        print(f"  Deleting {item}")
        if not DRY_RUN:
            subprocess.run(["poetry", "run", "pmc", key, "delete", item])
