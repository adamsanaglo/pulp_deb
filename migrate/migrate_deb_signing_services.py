#!/usr/bin/env python
# A helper script to do the one-time migration of deb signing services fields on the repos.
import requests
import sys

if len(sys.argv) < 2:
    print("Usage: ./migrate_deb_signing_services.py <pulp_service> <pulp_password>")
    print("<pulp_service> will typically be something like 'localhost:8080' or 'localhost:24817'")
    exit()

hostname = sys.argv[1]
auth = None
if len(sys.argv) == 3:
    from requests.auth import HTTPBasicAuth

    password = sys.argv[2]
    auth = HTTPBasicAuth("admin", password)

response = requests.get(
    "http://" + hostname + "/pulp/api/v3/repositories/deb/apt/", params={"limit": "500"}, auth=auth
)
for repo in response.json()["results"]:
    href = repo["pulp_href"]
    labels = repo.pop("pulp_labels", {})
    service = labels.pop("signing_service", None)
    if service:
        print(f"Updating {repo['name']} to {service}")
        repo["signing_service"] = service
        resp = requests.put("http://" + hostname + href, data=repo, auth=auth)
        print(resp)
