#!/usr/bin/python3

import json
import sys
import time
from functools import wraps
from tempfile import mkdtemp
from typing import Dict, List

import requests

from config import settings

sign_ip = settings["SIGNER_HOST"]
sign_port = "8888"
sign_endpoint = "sign"
signature_endpoint = "signature"
key_ids = {"esrp_test": "CP-450778-Pgp", "esrp_prod": "CP-450779-Pgp", "legacy": "legacy"}


def _bail(msg: str) -> None:
    """
    Write the specified message to stderr and exit with non-zero exit code.
    Pulp expects output on stdout, so this is the best way to end execution.
    """
    print(msg, file=sys.stderr)
    sys.exit(1)


def _format_output(filename: str, tmp_dir: str, apt: bool) -> str:
    """
    Generate a JSON string in the format that pulp expects it
    """
    result = {}
    if apt:
        # Apt repo, pulp_deb AptReleaseSigningService format
        # https://github.com/pulp/pulp_deb/blob/main/pulp_deb/app/models/signing_service.py
        result["signatures"] = {
            "inline": f"{tmp_dir}/InRelease",
            "detached": f"{tmp_dir}/Release.gpg",
        }
    else:
        # Yum repo, pulpcore AsciiArmoredDetachedSigningService format
        # https://github.com/pulp/pulpcore/blob/main/pulpcore/app/models/content.py
        result["file"] = filename
        result["signature"] = f"{tmp_dir}/repomd.xml.asc"
    return json.dumps(result)


class RetriableException(Exception):
    pass


def with_retries(original_function=None, *, max_attempts: int = 120):
    """
    This idiom defines a function decorator, `with_retries`, that can either be called with the
    max_attempts _kwarg_ or without. It must be a kwarg, not a positional arg.
    https://stackoverflow.com/questions/3888158/making-decorators-with-optional-arguments
    """

    def _decorate(function):
        @wraps(function)
        def wrapped_function(*args, **kwargs):
            attempt = 0
            last_ex = None
            while attempt < max_attempts:
                try:
                    return function(*args, **kwargs)
                except RetriableException as e:
                    last_ex = e
                    attempt += 1
                    time.sleep(10)
            # Max attempts exceeded
            raise last_ex

        return wrapped_function

    if original_function:
        return _decorate(original_function)
    return _decorate


@with_retries(max_attempts=3)
def _post_sign(params: dict, file_data: bytes) -> str:
    """
    Call out to the signer container to enqueue the signing job.
    Will retry if exception is raised (uncommon).
    Returns the task ID for this request.
    """
    url = f"http://{sign_ip}:{sign_port}/{sign_endpoint}"
    # Let exception filter up to trigger retry logic
    resp = requests.post(url, stream=False, params=params, files={"file": file_data})
    if resp.status_code != 200:
        raise RetriableException(
            f"Unrecognized status code received from {url}: {resp.status_code}"
        )
    detail = json.loads(resp.text)
    task_id = detail["x-ms-workflow-run-id"]
    return task_id


@with_retries
def _get_signature(task_id: str, apt: bool) -> str:
    """
    Call out to the signer container to fetch the results of the signing job.
    Will retry if exception is raised (common if job is not done yet).
    Returns the string path of the temporary directory where the signature(s) have been written.
    """
    url = f"http://{sign_ip}:{sign_port}/{signature_endpoint}"
    params = {"task_id": task_id}

    # Let exception filter up to trigger retry logic
    resp = requests.get(url, params=params)
    if resp.status_code == 400:
        # Task ID is unrecognized
        _bail(f"Unrecognized task id [{task_id}]: {resp.status_code}")
    if resp.status_code == 204:
        # Content isn't ready yet. Wait for retry.
        raise RetriableException(f"Signature not ready for task {task_id}: {resp.status_code}")
    if resp.status_code != 200:
        # Unknown status code. Retry.
        raise RetriableException(f"Unknown response code for task {task_id}: {resp.status_code}")
    # Write signature(s) to disk
    resp_json = json.loads(resp.text)
    tmpdir = mkdtemp()
    write_to_temporary_file(resp_json, "detached", apt, tmpdir)
    if apt:
        write_to_temporary_file(resp_json, "clearsigned", apt, tmpdir)
    return tmpdir


def write_to_temporary_file(resp: Dict[str, str], key: str, apt: bool, tmpdir: str) -> None:
    """
    Write the provided content to a temporary file, created securely via tempfile.
    The signing services are very particular about what these files MUST BE NAMED.
    """
    if apt:
        name = "InRelease" if key == "clearsigned" else "Release.gpg"
    else:
        name = "repomd.xml.asc"
    with open(f"{tmpdir}/{name}", "w") as f:
        f.write(resp[key])


def _read_file(filename: str) -> bytes:
    """
    Read the specified file as bytes
    """
    try:
        with open(filename, "rb") as f:
            file_data = f.read()
    except Exception as e:
        _bail(f"Failed to read unsigned file from disk: {e}")
    return file_data


def _parse_key_param(key_name) -> dict:
    """
    Parse the key id for the specified signing key
    """
    if not key_name in key_ids:
        _bail(f"Key name {key_id} unrecognized")
    return {"key_id": key_ids[key_name]}


def parse_parameters(args: List) -> str:
    """
    Parse the filename to sign from command-line params
    """
    if len(args) < 2:
        _bail("Must specify filename to sign")
    return args[1]


def sign_content(filename: str, key_name: str, apt: bool = False) -> str:
    """
    Generate a signature for the specified file
    Return a JSON string that will be used by Pulp
    """
    # Read file from disk
    file_data = _read_file(filename)
    params = _parse_key_param(key_name)
    params["clearsign"] = apt

    # Perform POST and poll for result, with retries
    try:
        task_id = _post_sign(params, file_data)
        time.sleep(1)  # Legacy signing is fast, it'll probably be done in a sec.
        tmp_dir = _get_signature(task_id, apt)
    except Exception as e:
        _bail(f"Failed to retrieve signature: {e}")
    # Output result
    return _format_output(filename, tmp_dir, apt)
