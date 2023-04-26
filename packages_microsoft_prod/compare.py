#!/usr/bin/python
# This simple script is intended to help test ensure that the config repos and symlinks in this
# directory match the "vCurrent" implementation in prod. It will simply crawl through the relevant
# directories and compare against prod, noting differences.
from typing import Callable, Generator, List, Set, Tuple
from bs4 import BeautifulSoup
import requests

LOCAL = "http://localhost:8081/"
PROD = "http://packages.microsoft.com/"


def get(url: str) -> BeautifulSoup:
    """Returned a BeautifulSoup-parsed representation of the url given."""
    response = requests.get(url)
    if response.status_code != 200:
        return BeautifulSoup("", "html.parser")
    return BeautifulSoup(response.content, "html.parser")


def process_list(bs: BeautifulSoup) -> List[str]:
    """
    Given a BeautifulSoup representation of a directory listing, return a list of contents excluding
    some we don't care about.
    """
    ret: List[str] = []
    if not bs:
        return ret
    for link in bs.find_all("a"):
        href = link["href"]
        if href in ("../", "Packages/", "repodata/", "config.repo", "dists/", "pool/"):
            continue
        ret.append(href)
    return ret


def prod_tree_walk(relative_path: str) -> Generator[Tuple[str, Set[str], Set[str]], None, None]:
    """
    Recursively follow the prod path down into all subdirs that it shares with local, yielding
    (relative_path, prod_contents, local_contents) at each step.
    """
    prod = process_list(get(PROD + relative_path))
    local = process_list(get(LOCAL + relative_path))
    yield relative_path, set(prod), set(local)

    for subdir in [x for x in prod if x.endswith("/") and x in local]:
        yield from prod_tree_walk(relative_path + subdir)


def compare_file(relative_path: str, content_filter: Callable[[str], str]) -> None:
    """
    Given a partial url to a file and a filter function, compare between prod and local and
    print differences.
    """
    prod = str(requests.get(PROD + relative_path).content, "utf-8")
    local = str(requests.get(LOCAL + relative_path).content, "utf-8")
    prod, local = content_filter(prod), content_filter(local)
    if prod != local:
        print(f"  {relative_path}:\n    Prod: {prod}\n    Local: {local}")


def list_filter(content: str) -> str:
    """
    There are going to be differences here because the individual list files didn't contain
    the signed-by clause. Parse it out and just compare the rest.
    """
    start, mid = content.split("[")
    mid, end = mid.split("]")
    # Ignore CR character in prod
    return (start + end).strip()


def repo_filter(content: str) -> str:
    """
    There are going to be differences here because for example we're naming the repos better and
    enabling sslverify for the non-prod repos, but we should check that the label and baseurl
    are the same.
    """
    return ", ".join(x for x in content.split("\n") if "[" in x or "baseurl" in x)


for top in ("config/", "centos/", "debian/", "fedora/", "opensuse/", "rhel/", "sles/", "ubuntu/"):
    for relative_path, set_prod, set_local in prod_tree_walk(top):
        print(f"Processing {relative_path}:")
        if set_prod - set_local:
            print(f"  Extra in prod: {set_prod - set_local}")
        if set_local - set_prod:
            print(f"  Extra in local: {set_local - set_prod}")
        for x in set_local.intersection(set_prod):
            if x.endswith(".list"):
                compare_file(relative_path + x, list_filter)
            elif x.endswith(".repo"):
                compare_file(relative_path + x, repo_filter)
