#!/usr/bin/python3
# This tool is used for Emergency Certificate rotation, and serves two purposes.
# 1. Generate a new certificate
# 2. Download the newly generated Certificate
# This uses MSI and assumes the VM's identity has appropriate permission
# to perform both of the above operations.

import click
import json
import os
import tempfile
import util

from keyvault_util import keyvault_util
from pathlib import Path

@click.command()
@click.argument('file_path')
@click.option('-r', '--rotate', is_flag=True,
              help='Rotate the specified cert(s)')
@click.option('-d', '--download', is_flag=True,
              help='Download the specified cert(s)')
@click.option('-a', '--azclitoken', is_flag=True,
              help='Use token from az cli instead of MSI')
def main(rotate: bool, download: bool, azclitoken: bool, file_path: str):
    """
    Parse parameters and initiate execution
    """
    if not rotate and not download:
        bail("Must specify -r and/or -d")
    json_file = Path(file_path)
    if not json_file.is_file():
        bail(f"File {file_path} is not a valid file.")
    with open(json_file, "r") as f:
        config = json.load(f)
    try:
        process_certificates(rotate, download, azclitoken, config)
    except Exception as e:
        bail(f"Failed to perform one or more operations: {str(e)}")


def write_cert_to_file(downloaded_cert: str, cert_path: str):
    """
    Securely create the specified cert file and write
    cert contents to it.
    """
    # Create the file
    open(cert_path, 'a').close()
    # Set permissions
    os.chmod(cert_path, 0o600)
    # Write cert to file
    with open(cert_path, "w") as f:
        f.write(downloaded_cert)


def get_azcli_token() -> str:
    """
    Retrieve keyvault token from az cli instead of MSI
    Primarily used for testing on-prem.
    """
    cmd = "az account get-access-token --resource https://vault.azure.net"
    res = util.run_cmd_out(cmd)
    if res.returncode != 0:
        bail(f"Error running [{cmd}]: {res.stderr}")
    try:
        parsed_result = json.loads(res.stdout)
        return parsed_result["accessToken"]
    except json.JSONDecodeError as e:
        bail(f"Failed to parse access token: {str(e)}")


def process_certificates(rotate: bool, download: bool, use_azcli_token: bool, config: dict):
    """
    Rotate and/or download each certificate in config
    """
    if use_azcli_token:
        token = get_azcli_token()
        kv_util = keyvault_util(token=token)
    else:
        kv_util = keyvault_util()
    if download:
        temp_dir = tempfile.mkdtemp()
    for vault in config:
        for cert_name in config[vault]:
            if rotate:
                click.echo(f"Rotating {vault}: {cert_name}...", nl=False)
                kv_util.rotate_cert(vault, cert_name)
                click.echo(f"Done")
            if download:
                click.echo(f"Downloading {vault}: {cert_name}...", nl=False)
                downloaded_cert = kv_util.get_secret(vault, cert_name)
                cert_path = Path(temp_dir) / f"{cert_name}.pem"
                write_cert_to_file(downloaded_cert, cert_path)
                click.echo(f"to {cert_path}")


def bail(msg: str):
    """
    Emit the specified message on stderr and exit
    """
    click.echo(msg, err=True)
    exit(1)


if __name__ == '__main__':
    main()
