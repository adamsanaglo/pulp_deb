from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import tempfile
from typing import List, Optional, Tuple

import azure.functions as func
from repoaudit.utils import destroy_gpg, initialize_gpg, RepoErrors
from repoaudit.apt import _find_dists
import requests
from requests.exceptions import HTTPError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TRUSTED_CA = '''
# Issuer: CN=DigiCert Global Root G2 O=DigiCert Inc OU=www.digicert.com
# Subject: CN=DigiCert Global Root G2 O=DigiCert Inc OU=www.digicert.com
# Label: "DigiCert Global Root G2"
# Serial: 4293743540046975378534879503202253541
# MD5 Fingerprint: e4:a6:8a:c8:54:ac:52:42:46:0a:fd:72:48:1b:2a:44
# SHA1 Fingerprint: df:3c:24:f9:bf:d6:66:76:1b:26:80:73:fe:06:d1:cc:8d:4f:82:a4
# SHA256 Fingerprint: ''' \
'''cb:3c:cb:b7:60:31:e5:e0:13:8f:8d:d3:9a:23:f9:de:47:ff:c3:5e:43:c1:14:4c:ea:27:d4:6a:5a:b1:cb:5f
-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ
vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP
BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4
NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG
Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91
8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe
pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl
MrY=
-----END CERTIFICATE-----
'''


@contextmanager
def load_ca() -> str:
    """Context manager to create a certificate file and then destroy it upon exiting."""
    trusted_ca_file = tempfile.NamedTemporaryFile(
        prefix="cacert_",
        suffix=".cer",
        delete=False,
        mode="w"
    )

    try:
        try:
            logging.info(f"CA path is {trusted_ca_file.name}")
            trusted_ca_file.write(TRUSTED_CA)
        finally:
            # we close the file before yielding since some systems like Windows
            # do not like having the same file open twice.
            trusted_ca_file.close()

        yield trusted_ca_file.name
    finally:
        Path(trusted_ca_file.name).unlink()


@contextmanager
def load_gpg(pubkeys: List[str], verify: Optional[str] = None) -> None:
    """Context manager to initialize gpg object and then destroy it upon exiting."""
    gpg = initialize_gpg(pubkeys, verify=verify)

    try:
        yield gpg
    finally:
        destroy_gpg(gpg)


def log_message(msg: func.QueueMessage) -> None:
    """Log message content and information."""
    logging.info(json.dumps({
        'id': msg.id,
        'body': msg.get_body().decode('utf-8'),
        'expiration_time': (msg.expiration_time.isoformat()
                            if msg.expiration_time else None),
        'insertion_time': (msg.insertion_time.isoformat()
                           if msg.insertion_time else None),
        'time_next_visible': (msg.time_next_visible.isoformat()
                              if msg.time_next_visible else None),
        'pop_receipt': msg.pop_receipt,
        'dequeue_count': msg.dequeue_count
    }))


def get_apt_filter(urls: List[str], verify: Optional[str] = None) -> dict:
    """Generates a filter of apt repositories and dists."""
    repo_filter = dict()
    for url in urls:
        try:
            dists = list(_find_dists(url, verify=verify))
        except HTTPError:
            dists = []
        repo_filter[url] = dists
    return repo_filter


def get_yum_filter(urls: List[str]) -> dict:
    """Generates a filter of yum repositories."""
    repo_filter = dict()
    for url in urls:
        dists = [RepoErrors.YUM_DIST]
        repo_filter[url] = dists
    return repo_filter


def get_repo_from_msg(msg: func.QueueMessage) -> Tuple[str, str]:
    """Get repo type and url from a msg and raise an error if no type or url is found."""
    message = msg.get_body().decode('utf-8')
    message_json = json.loads(message)
    if 'type' not in message_json:
        raise Exception(f'Message does not contain a "type" entry: {message}')

    if 'repo' not in message_json:
        raise Exception(f'Message does not contain a "repo" entry: {message}')

    repo = message_json['repo']
    type = message_json['type']
    return type, repo


def check_date(
    file_url: str,
    last_checked: Optional[datetime],
    hours_until_recheck: int = 672,  # 4 weeks between full re-scans
    shift_last_checked: int = -4
) -> bool:
    """
    Returns True if a metadata file's last modified time indicates a repository
    should be checked, False otherwise.
    """
    if last_checked is None:
        return True

    # Shift last_checked time to account for updates occurring during the check.
    # At the moment, last_checked represents the end time of the status check
    # which could theoretically take up to 4 hours (the timeout of the function).
    last_checked = last_checked + timedelta(hours=shift_last_checked)

    # re-scan if repository is empty
    try:
        response = request_headers(file_url)
    except HTTPError:
        return True

    last_modified_str = response.headers.get('Last-Modified', None)

    if not last_modified_str:
        return True

    try:
        last_modified = datetime.strptime(last_modified_str, '%a, %d %b %Y %H:%M:%S %Z')
    except ValueError:
        logging.warning(
            f"Could not parse Last-Modified header for '{file_url}': '{last_modified_str}'"
        )
        return True

    time_now = datetime.utcnow()

    # re-scan if repository status is stale
    hours_since_last_check = (time_now-last_checked).total_seconds() // 3600
    if hours_since_last_check >= hours_until_recheck:
        return True

    # re-scan if changes have been made since the last check
    if last_modified >= last_checked:
        return True

    return False


def get_datetime(
    repo_type: str,
    repo: str,
    dist: str,
    current_status: dict
) -> Optional[datetime]:
    """Construct datetime object representing last updated time for a repo and dist."""
    try:
        time_str = current_status[repo_type][repo]["dists"][dist]["time"]
    except (TypeError, KeyError):
        return None

    try:
        date = datetime.fromisoformat(time_str)
    except ValueError:
        logging.warning(
            f"Could not parse time for {repo_type} repo {repo} at dist {dist} : '{time_str}'"
        )
        return None

    return date


def repo_needs_status_update(
    repo_type: str,
    repo_url: str,
    current_status: dict,
    dists: List[str] = None
) -> bool:
    """
    Check if apt or yum repo/dist needs a status update based on the last time it
    was checked according to the current_status which is intended to be the same as
    the current repository_status.json.
    """
    assert repo_type == "apt" or repo_type == "yum"

    if repo_type == "apt":
        if not dists:
            return True

        for dist in dists:
            release_url = urljoin(repo_url, "dists", dist, "Release")
            last_checked = get_datetime(repo_type, repo_url, dist, current_status)
            if check_date(release_url, last_checked):
                return True
    else:
        repomd_url = urljoin(repo_url, "repodata", "repomd.xml")
        last_checked = get_datetime(repo_type, repo_url, RepoErrors.YUM_DIST, current_status)
        if check_date(repomd_url, last_checked):
            return True

    return False


def check_and_add_task(task: dict, tasks: list, current_status: dict) -> bool:
    """
    Add an apt or yum task to the tasks list only if the repo/dist
    status in current_status is out of date or stale.
    """
    repo_type = task.get("type", None)
    repo = task.get("repo", None)
    assert repo_type is not None and repo is not None

    dists = task.get("dists", None)

    if repo_needs_status_update(repo_type, repo, current_status, dists=dists):
        tasks.append(json.dumps(task))


def get_dists_from_msg(msg: func.QueueMessage) -> Optional[List[str]]:
    """Get dists from msg."""
    message_json = json.loads(msg.get_body().decode('utf-8'))

    dists = None
    if 'dists' in message_json and message_json['dists']:
        dists = set(message_json['dists'])

    return dists


def get_status_msg(status: dict, status_type: str) -> str:
    """Get the status message to add to the results-queue."""
    output = {"status_type": status_type, "status": status}
    return json.dumps(output, indent=4)


def urljoin(*paths: str) -> str:
    """Join together a set of url components."""
    # urllib's urljoin has a few gotchas and doesn't handle multiple paths
    return "/".join(map(lambda path: path.strip("/"), paths))


def retry_session(retries: int = 3) -> requests.Session:
    """Create a requests.Session with retries."""
    session = requests.Session()
    retry = Retry(total=retries)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def request_headers(
    url: str,
    session: Optional[requests.Session] = None,
    verify: Optional[str] = None
) -> requests.Response:
    """Call requests.head() on a url and return the requests.Response."""
    if not session:
        session = retry_session()
    resp = session.head(url, verify=verify)
    resp.raise_for_status()
    return resp
