#!/usr/bin/python3

import json
import requests
import sys
import time

from functools import wraps
from tempfile import mkstemp
from typing import List

max_attempts = 20
sign_ip = "127.0.0.1"
sign_port = "8888"
sign_endpoint = "sign"
signature_endpoint = "signature"
key_ids = {
    "esrp_test": "CP-450778-Pgp",
    "esrp_prod": "CP-450779-Pgp",
    "legacy": "legacy"
}


def _bail(msg: str) -> None:
    """
    Write the specified message to stderr and exit with non-zero exit code.
    Pulp expects output on stdout, so this is the best way to end execution.
    """
    print(msg, file=sys.stderr)
    sys.exit(1)


def _format_output(filename: str, sig_file: str) -> str:
    """
    Generate a JSON string in the format that pulp expects it
    """
    result = {
        "file": filename,
        "signature": sig_file
    }
    return json.dumps(result)


def with_retries(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        attempt = 0
        last_ex = None
        while attempt < max_attempts:
            try:
                return f(*args, **kwargs)
            except Exception as e:
                last_ex = e
                attempt += 1
                time.sleep(60)
        # Max attempts exceeded
        raise last_ex
    return wrapper
    

@with_retries
def _post_sign(params: dict, file_data: bytes) -> str:
    """
    Convenience method for posting files for signing
    Returns the task ID for this request
    """
    url = f"http://{sign_ip}:{sign_port}/{sign_endpoint}"
    # Let exception filter up to trigger retry logic
    resp = requests.post(url, stream=False, params=params, files={"file": file_data})
    if resp.status_code != 200:
        raise Exception(f"Unrecognized status code received from {url}: {resp.status_code}")
    detail = json.loads(resp.text)
    task_id = detail['x-ms-workflow-run-id']
    return task_id


@with_retries
def _get_signature(task_id: str) -> str:
    """
    Convenience method for getting signature from API
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
        raise Exception(f"Signature not ready for task {task_id}: {resp.status_code}")
    if resp.status_code != 200:
        # Unknown status code. Retry.
        raise Exception(f"Unknown response code for task {task_id}: {resp.status_code}")
    # Write signature to disk
    resp_json = json.loads(resp.text)
    out_file = write_to_temporary_file(resp_json['content'])
    return out_file
    

def write_to_temporary_file(content: str) -> str:
    """
    Write the provided content to a temporary file,
    created securely via tempfile
    """
    tmpfile = mkstemp()
    with open(tmpfile[1], 'w') as f:
        f.write(content)
    return tmpfile[1]


def _read_file(filename: str) -> bytes:
    """
    Read the specified file as bytes
    """
    try:
        with open(filename, 'rb') as f:
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
    return {
        "key_id": key_ids[key_name]
    }


def parse_parameters(args: List) -> str:
    """
    Parse the filename to sign from command-line params
    """
    if len(args) < 2:
        _bail("Must specify filename to sign")
    return args[1]


def sign_content(filename: str, key_name: str) -> str:
    """
    Generate a signature for the specified file
    Return a JSON string that will be used by Pulp
    """
    # Read file from disk
    file_data = _read_file(filename)
    params = _parse_key_param(key_name)

    # Perform POST and poll for result, with retries
    try:
        task_id = _post_sign(params, file_data)
        sig_file = _get_signature(task_id)
    except Exception as e:
        _bail(f"Failed to retrieve signature: {e}")
    # Output result
    return _format_output(filename, sig_file)
