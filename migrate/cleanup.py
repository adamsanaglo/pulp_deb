#!/usr/bin/env python
# A script that will cleanup old (ie not latest) repo versions and publications
#
# This is helpful for removing orphaned content which cannot be cleaned up if it's attached to a
# repo version or publication. Publications are cleaned up here indirectly; deleting a repo version
# will delete its publications.
#
# Because this script uses 'retain_repo_versions', this script should NOT be used once publishers
# start using the API. Up until now, the latest repo version IS the distributed version but once
# publishers use the API, this may not be the case.
#
# For more info, see:
#
# https://github.com/pulp/pulpcore/issues/2705

import json
import subprocess
import sys

DRY_RUN = True
if len(sys.argv) >= 2 and sys.argv[1] == "--for-real":
    DRY_RUN = False
else:
    print("Executing dry run. Use '--for-real' to disable.\n")

BATCH_SIZE = 50

cleanup_count = 0


def poetry_cmd(cmd):
    res = subprocess.run(
        ["poetry", "run"] + cmd,
        capture_output=True,
    )
    return res


def list_cmd(resource, offset=0, batch_size=BATCH_SIZE, filters=[]):
    if isinstance(resource, str):
        resource = [resource]

    cmd = [
        "pmc",
        *resource,
        "list",
        "--limit",
        str(batch_size),
        "--offset",
        str(offset),
    ]
    if filters:
        cmd += filters
    res = poetry_cmd(cmd)
    obj = json.loads(res.stdout)
    return obj


def repos():
    offset = 0
    while True:
        ret = list_cmd("repo", offset)
        yield [(repo["id"], repo["name"]) for repo in ret["results"]]
        offset += BATCH_SIZE
        if offset >= ret["count"]:
            break


def repo_version_count(repo_id):
    ret = list_cmd(["repository", "version"], batch_size=1, filters=["--repo", repo_id])
    return ret["count"]


for batch in repos():
    for repo_id, repo_name in batch:
        print(f"Checking repo '{repo_name}'.")
        rv_count = repo_version_count(repo_id)
        if rv_count <= 1:
            print(f"Found {rv_count} versions for '{repo_name}'. Skipping.\n")
            continue

        if not DRY_RUN:
            poetry_cmd(["pmc", "repo", "update", repo_id, "--retain-repo-versions", "1"])
            poetry_cmd(["pmc", "repo", "update", repo_id, "--retain-repo-versions", ""])
            new_rv_count = repo_version_count(repo_id)
            cleanup_count += rv_count - new_rv_count
            print(f"Cleaned up {rv_count - new_rv_count} versions for '{repo_name}'.")
        else:
            print(f"Would cleanup {rv_count-1} versions for '{repo_name}'.")

        print("")


print(f"Done. Cleaned up {cleanup_count} versions.")
print("Now run 'pmc orphan cleanup' to remove old content.")
