import json
import logging
import util

from config import settings
from datetime import datetime, timedelta
from enum import Enum
from keyvault_util import keyvault_util
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Dict

log = logging.getLogger('uvicorn')
esrp_config_files = {
}
esrp_auth_cert_path = ''
esrp_cert_retrieved_time = None
esrp_cert_cache_timeout = timedelta(hours=1)
azlogin_timeout = timedelta(hours=1)
azlogin_expiration = datetime.min


class ESRPAuthException(Exception):
    pass


class SigningOperation(Enum):
    # Pulp should only require detached signatures...
    attached = 'PgpClearsign'
    detached = 'LinuxSign'


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
    log.info('Checking ESRP config')
    if config_index in esrp_config_files and \
        esrp_config_files[config_index] and \
        Path(esrp_config_files[config_index]).is_file():
        log.info('Using ESRP config from cache')
        return esrp_config_files[config_index]

    # Generate a config file used by ESRP
    log.info('Generating ESRP config')
    try:
        esrp_sig_config = get_esrp_config_template(settings, key_id, operation.value)
    except KeyError as e:
        log.error(f'Unable to generate esrp config: {e}')
        raise
    # Write to file
    log.info('Writing esrp config')
    config_bytes = json.dumps(esrp_sig_config).encode()
    esrp_config_files[config_index] = util.write_to_temporary_file(config_bytes, 'json')
    log.info(f'Wrote esrp {config_index} config to {esrp_config_files[config_index]}')
    return esrp_config_files[config_index]


def get_esrp_config_template(settings: dict, key_id: str, operation: str) -> Dict:
    """
    Return esrp template that will be populated with values
    """
    esrp_sig_config = {
        "clientId": settings.APP_ID,
        "gatewayApi": "https://api.esrp.microsoft.com",
        "requestSigningCert": {
            "subject": settings.SIGN_CERT,
            "vaultName": settings.KEYVAULT
        },
        "driEmail": ["aztuxrepo@microsoft.com"],
        "signingOperations": [
            {
                "keyCode": key_id,
                "operationSetCode": operation,
                "parameters": [],
                "toolName": "sign",
                "toolVersion": "1.0"
            }
        ],
        "hashType": "sha256"
    }
    return esrp_sig_config


def get_esrp_auth_cert_to_file() -> str:
    """
    Writes the esrp Authentication cert to a temporary file on disk
    """
    global esrp_auth_cert_path, esrp_cert_retrieved_time
    if esrp_auth_cert_path and Path(esrp_auth_cert_path).is_file():
        # There are cached credentials; decide whether to use them
        elapsed = datetime.utcnow() - esrp_cert_retrieved_time
        if elapsed < esrp_cert_cache_timeout:
            # Cache is still fresh
            return esrp_auth_cert_path
    vault_name = settings.KEYVAULT
    cert_name = settings.AUTH_CERT
    kv_util = keyvault_util()
    auth_cert = kv_util.get_secret(vault_name, cert_name)
    esrp_auth_cert_path = util.write_to_temporary_file(auth_cert.encode(), 'pem')
    esrp_cert_retrieved_time = datetime.utcnow()
    return esrp_auth_cert_path


def az_login():
    """
    Login to az cli
    """
    global azlogin_expiration, azlogin_timeout
    if datetime.utcnow() < azlogin_expiration:
        # Session is still fresh
        return
    auth_app_id = settings.APP_ID
    auth_tenant = settings.TENANT_ID
    auth_cert_path = get_esrp_auth_cert_to_file()
    cmd_split = ['az',
                 'login',
                 '--service-principal',
                 '--use-cert-sn-issuer',
                 '-u', auth_app_id,
                 '-p', auth_cert_path,
                 '--tenant', auth_tenant,
                 '--allow-no-subscriptions']
    log.info('Running az login')
    if not util.run_cmd(cmd_split):
        raise ESRPAuthException('Failed to run az login')
    azlogin_expiration = datetime.utcnow() + azlogin_timeout


def az_xsign(src_file: str, dst_file: str, operation: SigningOperation, key_id: str) -> bool:
    """
    Push src_file to ESRP for signing,
    write the resultant signature to dst_file
    """
    esrp_config = get_esrp_config(operation, key_id)
    cmd_split = ['az',
                 'xsign',
                 'sign-file',
                 '--file-name', src_file,
                 '--signed-file-name', dst_file,
                 '--config-file', esrp_config]
    log.info('Running az xsign')
    if not util.run_cmd(cmd_split):
        raise Exception('Failed to run az xsign')


def write_unsigned_file_to_disk(unsigned_file: SpooledTemporaryFile) -> str:
    """
    API represents incoming files as SpooledTemporaryFile (in memory),
    but ESRP expects a file on disk. So, write the bytes to disk.
    """
    out_file = util.get_temporary_file()
    with open(out_file, 'wb') as f:
        f.write(unsigned_file.read())
    return out_file


def sign_content(unsigned_file: SpooledTemporaryFile, operation: SigningOperation, key_id: str) -> str:
    """
    Submits the specified file for signing,
    and returns the path to the generated signature
    """
    dst_file = util.get_temporary_file('gpg')
    unsigned_file_name = write_unsigned_file_to_disk(unsigned_file)
    az_login()
    az_xsign(unsigned_file_name, dst_file, operation, key_id)
    util.secure_delete(unsigned_file_name)
    return dst_file
