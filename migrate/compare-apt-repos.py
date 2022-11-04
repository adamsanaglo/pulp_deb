#!/usr/bin/env python
# A helper script to iterate through all apt repos in vCurrent and compare with vNext to ensure
# we aren't missing anything.

import sys
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

VERBOSE = False
if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
    VERBOSE = True

VCURRENT = "http://packages.microsoft.com/repos/"
VNEXT = "http://pmc-distro.trafficmanager.net/repos/"
# VNEXT = "http://localhost:8081/repos/"


def get(url):
    # print("Fetching " + url)
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return BeautifulSoup(response.content, "html.parser")


def process_list(bs):
    ret = []
    if not bs:
        return ret
    for link in bs.find_all("a"):
        href = link["href"]
        if href.startswith(".."):
            continue
        ret.append(href)
    return ret


def package_dir_walk(_url, dir):
    url = _url + dir
    ret = set()
    items = process_list(get(url))
    # recursion termination scenario, dead-end or list of files
    if not items or not items[0].endswith("/"):
        return set([url + x for x in items])
    # else another list of subdirs
    for dir in items:
        ret.update(package_dir_walk(url, dir))
    return ret


def find_packages_files(_url, dir):
    url = _url + dir
    ret = set()
    items = process_list(get(url))
    for item in items:
        if item == "Packages":
            ret.add(url + item)
        elif item.endswith("/"):
            ret.update(find_packages_files(url, item))
    return ret


def process_packages_file(response):
    # returns a dict of sha256 hash to filepath
    packages = {}
    content = str(response.content, "utf-8")
    hash = ""
    filename = ""
    for line in content.split("\n"):
        if line.startswith("Package: "):
            if hash:
                packages[hash] = filename
            hash = ""
            filename = ""
        if line.startswith("SHA256: "):
            hash = line.split(": ")[-1]
        if line.startswith("Filename: "):
            filename = line.split(": ")[-1]
    if hash:
        packages[hash] = filename
    return packages


def get_archless_packages(all_package_cache, url):
    component_url, _, _ = url.rsplit("/", 2)
    if not component_url in all_package_cache:
        # don't re-fetch the archless package list every arch, fetch it once and cache
        response = requests.get(component_url + "/binary-all/Packages")
        if response.status_code == 200:
            all_package_cache[component_url] = process_packages_file(response)
        else:
            all_package_cache[component_url] = {}
    return all_package_cache[component_url]


# 1) Get list of repos from vCurrent
# repos = ["cyclecloud/", "cyclecloud-insiders/"]
repos = process_list(get(VCURRENT))
for repo in repos:
    print("Processing " + repo)
    # 2) Quit early if it's an empty repo
    if not get(VCURRENT + repo):
        print("  ...Invalid repo on vCurrent. Skipping.")
        continue
    if not get(VNEXT + repo):
        current_packages = package_dir_walk(VCURRENT, repo + "pool/")
        # if the repo in vCurrent contains at least one package the it does't exist in vNext,
        # we should warn.
        if current_packages:
            print("  ...repo does not exist in vNext. Intentional?")
        else:
            print("  ...empty repo on vCurrent. Skipping.")
        continue
    # 3) Compare Package file lists
    referenced_packages = set()
    vnext_all_arch_packages: Dict[str, Dict[str, str]] = {}
    vcurrent_all_arch_packages: Dict[str, Dict[str, str]] = {}
    for url in sorted(find_packages_files(VCURRENT, repo + "dists/")):
        if "binary-all/" in url:
            # special handing for 'all' arch packages below. Skip for now.
            continue
        file = url.removeprefix(VCURRENT)
        response = requests.get(VNEXT + file)
        if response.status_code != 200:
            print("  ...Packages file missing in vNext: " + file)
            continue
        next_pf = process_packages_file(response)
        current_pf = process_packages_file(requests.get(VCURRENT + file))
        # vCurrent sometimes sorts architecture="all" packages into each arch's Packages file and
        # sometimes puts them in a binary-all/Packages file, while vNext always puts them in a
        # separate binary-all/Packages file. Both are valid from a cli perspective. Normalize by
        # adding back in the all arch packages to each arch-specific file so we can compare.
        next_pf.update(get_archless_packages(vnext_all_arch_packages, VNEXT + file))
        current_pf.update(get_archless_packages(vcurrent_all_arch_packages, VCURRENT + file))
        if next_pf.keys() != current_pf.keys():
            print("  ...discrepancy in Packages file! " + file)
            if VERBOSE:
                missing = current_pf.keys() - next_pf.keys()
                extra = next_pf.keys() - current_pf.keys()
                if missing:
                    print(f"    ...vNext is missing: {missing}")
                if extra:
                    print(f"    ...vNext has extra: {extra}")
        referenced_packages.update(next_pf.values())
    # This is fairly slow and we probably shouldn't bother. We're not testing Pulp here. Assume
    # that pulp is creating correct repodata.
    # 4) Ensure all reference packages actually exist
    # listed_packages = package_dir_walk(VNEXT, repo + "pool/")
    # listed_packages = set([x.removeprefix(VNEXT + repo) for x in listed_packages])
    # if referenced_packages != listed_packages:
    #    missing = referenced_packages - listed_packages
    #    if missing:
    #        print(f"  ...vNext references packages that are not listed! {missing}")
