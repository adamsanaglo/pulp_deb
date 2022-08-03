from contextlib import contextmanager
import json
import logging
from pathlib import Path
import tempfile
from typing import List, Optional, Tuple

import azure.functions as func
from repoaudit.utils import destroy_gpg, initialize_gpg, RepoErrors
from repoaudit.apt import _find_dists
from requests.exceptions import HTTPError

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
