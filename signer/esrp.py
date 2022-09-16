import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict

import util
from config import Settings, settings

log = logging.getLogger("uvicorn")
esrp_config_files = {}
azlogin_timeout = timedelta(hours=1)
azlogin_expiration = datetime.min


class ESRPAuthException(Exception):
    pass


class SigningOperation(Enum):
    # Pulp should only require detached signatures...
    attached = "PgpClearsign"
    detached = "LinuxSign"


def get_esrp_config(operation: SigningOperation, key_id: str) -> str:
    """
    Returns the path to an ESRP JSON config file that
    is used for signing. It is written to the disk when first
    requested, and re-used on subsequent requests.
    2 separate files depending on the signing operation
    (attached vs detached)
    File contains no secrets
    """
    global esrp_config_files
    config_index = f"{operation.name}_{key_id}"
    log.info("Checking ESRP config")
    if (
        config_index in esrp_config_files
        and esrp_config_files[config_index]
        and Path(esrp_config_files[config_index]).is_file()
    ):
        log.info("Using ESRP config from cache")
        return esrp_config_files[config_index]

    # Generate a config file used by ESRP
    log.info("Generating ESRP config")
    try:
        esrp_sig_config = get_esrp_config_template(settings, key_id, operation.value)
    except KeyError as e:
        log.error(f"Unable to generate esrp config: {e}")
        raise
    # Write to file
    log.info("Writing esrp config")
    config_bytes = json.dumps(esrp_sig_config).encode()
    esrp_config_files[config_index] = util.write_to_temporary_file(config_bytes, "json")
    log.info(f"Wrote esrp {config_index} config to {esrp_config_files[config_index]}")
    return esrp_config_files[config_index]


def get_esrp_config_template(settings: Settings, key_id: str, operation: str) -> Dict:
    """
    Return esrp template that will be populated with values
    """
    esrp_sig_config = {
        "clientId": settings.APP_ID,
        "gatewayApi": "https://api.esrp.microsoft.com",
        "requestSigningCert": {"subject": settings.SIGN_CERT, "vaultName": settings.KEYVAULT},
        "driEmail": ["aztuxrepo@microsoft.com"],
        "signingOperations": [
            {
                "keyCode": key_id,
                "operationSetCode": operation,
                "parameters": [],
                "toolName": "sign",
                "toolVersion": "1.0",
            }
        ],
        "hashType": "sha256",
    }
    return esrp_sig_config


def az_login():
    """
    Login to az cli
    """
    global azlogin_expiration, azlogin_timeout
    if datetime.utcnow() < azlogin_expiration:
        # Session is still fresh
        return
    cmd = (
        f"az login --service-principal --use-cert-sn-issuer -u {settings.APP_ID} "
        f"-p {settings.AUTH_CERT_PATH} --tenant {settings.TENANT_ID} --allow-no-subscriptions"
    )
    log.info("Running az login")
    if not util.run_cmd(cmd):
        raise ESRPAuthException("Failed to run az login")
    azlogin_expiration = datetime.utcnow() + azlogin_timeout


def az_xsign(src_file: str, dst_file: str, operation: SigningOperation, key_id: str) -> None:
    """
    Push src_file to ESRP for signing,
    write the resultant signature to dst_file
    """
    esrp_config = get_esrp_config(operation, key_id)
    cmd = (
        "az xsign sign-file "
        f"--file-name {src_file} --signed-file-name {dst_file} --config-file {esrp_config}"
    )
    log.info("Running az xsign")
    if not util.run_cmd(cmd):
        raise Exception("Failed to run az xsign")
