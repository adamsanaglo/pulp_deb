import logging
from abc import abstractmethod
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Dict

from azure.core.exceptions import ClientAuthenticationError
from redis import Redis
from retrying import retry

import esrp
import util
from config import is_valid_keycode, settings

redis = Redis(host="localhost")
log = logging.getLogger("uvicorn")


def get_working_dir_key(task_id: str) -> str:
    return f"{task_id}_working_dir"


class AbstractSigner:
    # some filename constants that we can reference
    UNSIGNED_FILE = "unsigned_file"
    DETACHED_SIG = "detached"
    CLEARSIGNED_FILE = "clearsigned"

    def __init__(self, clearsign: bool, key_id: str, task_id: str, working_dir: str) -> None:
        self.clearsign = clearsign
        self.key_id = key_id
        self.task_id = task_id
        self.working_dir = working_dir

    def sign(self) -> bool:
        succeeded = True
        try:
            if self.clearsign:
                succeeded = self._sign(esrp.SigningOperation.attached, self.CLEARSIGNED_FILE)
            if succeeded:  # no point in requesting the second signature if we already failed
                succeeded = self._sign(esrp.SigningOperation.detached, self.DETACHED_SIG)
        except Exception as e:
            log.error(f"Fatal error signing with {self.key_id} key for task {self.task_id}: {e}")
            succeeded = False
        if succeeded:
            redis.set(get_working_dir_key(self.task_id), self.working_dir)
        else:
            util.shred_working_dir(Path(self.working_dir))
        return succeeded

    @abstractmethod
    def _sign(self, operation: esrp.SigningOperation, filename: str) -> bool:
        raise NotImplementedError


class LegacySigner(AbstractSigner):
    """Sign things locally with the gpg key specified in settings."""
    def __init__(self, clearsign: bool, key_id: str, task_id: str, working_dir: str) -> None:
        super().__init__(clearsign, key_id, task_id, working_dir)

        # Ensure that the legacy key has been imported.
        _import_legacy_key()

    def _import_legacy_key():
        # Check for the legacy signing key
        res = util.run_cmd_out("/usr/bin/gpg --list-secret-keys")
        if res.returncode != 0:
            # Failure listing keys? Try to proceed...
            log.error(f"Exit code {res.returncode} checking gpg key: {res.stderr}")
        if settings.LEGACY_KEY_THUMBPRINT in res.stdout:
            log.debug(f"Found key with thumbprint {settings.LEGACY_KEY_THUMBPRINT}")
            return

        # Import the key to gpg and delete the file from disk
        log.info("Importing legacy key from disk")
        # Let the caller handle the exception, i.e. if file is not B64
        decoded_key = util.decodeB64ToFile(settings.LEGACY_KEY_PATH)
        res = util.run_cmd_out(f"/usr/bin/gpg --import {decoded_key}")
        util.shred_file(decoded_key)
        if res.returncode != 0:
            # Failure importing key
            raise Exception(f"Error importing gpg key: {res.stderr}")

    def _sign(self, operation: esrp.SigningOperation, filename: str) -> bool:
        signature_option = "--detach-sign"
        if operation == esrp.SigningOperation.attached:
            signature_option = "--clearsign"

        cmd = (
            f"gpg --quiet --batch --yes --digest-algo SHA256 {signature_option} "
            f"--default-key {settings.LEGACY_KEY_THUMBPRINT} --armor "
            f"--output {self.working_dir}/{filename} {self.working_dir}/{self.UNSIGNED_FILE}"
        )
        res = util.run_cmd_out(cmd)
        if res.returncode != 0:
            raise Exception(f"Error signing with legacy key: {res.stderr}")
        return True


class ESRPSigner(AbstractSigner):
    """Call out to "az xsign" to get ESRP to sign the file for us."""
    @retry(stop_max_attempt_number=10, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def _sign(self, operation: esrp.SigningOperation, filename: str) -> bool:
        """
        Retry the request up to 10 times with exponential backoff
        """
        try:
            log.info(f"Generating {operation.name} signature for {self.task_id}")
            esrp.az_login()
            esrp.az_xsign(f"{self.working_dir}/{self.UNSIGNED_FILE}", 
                f"{self.working_dir}/{filename}", operation, self.key_id)
            log.info(f"Successfully signed file for {self.task_id}")
        except (esrp.ESRPAuthException, ValueError, ClientAuthenticationError) as e:
            # Non-retriable errors
            log.error(f"[{type(e)}] Fatal error handling request for task [{self.task_id}]: {e}")
            return False
        except Exception as e:
            # Re-raise exception, which will trigger retry logic.
            log.error(f"[{type(e)}] Retriable error for task [{self.task_id}]: {e}")
            raise
        return True


def sign_request(
        unsigned_file: SpooledTemporaryFile, clearsign: bool, key_id: str, task_id: str
    ) -> bool:
    """
    Write the unsigned file to disk
    Submit it to ESRP for signing
    Store the signature for return to the requestor
    """
    working_dir = util.create_working_dir(unsigned_file, AbstractSigner.UNSIGNED_FILE)
    if key_id == "legacy":
        return LegacySigner(clearsign, key_id, task_id, working_dir).sign()
    if not is_valid_keycode(key_id):
        log.error(f"Key code {key_id} is not in the list of supported keys for task [{task_id}]")
    return ESRPSigner(clearsign, key_id, task_id, working_dir).sign()


def get_signature_file(task_id: str) -> Dict:
    """
    Generate a Dict containing the signature(s) for the specified task id
    """
    response = {"detached": ""}
    working_dir_key = get_working_dir_key(task_id)
    if not redis.exists(working_dir_key):
        log.error(f"Key {working_dir_key} not present in Redis")
        return response
    working_dir = Path(redis.get(working_dir_key).decode("utf-8"))
    with open(working_dir / AbstractSigner.DETACHED_SIG, "r") as f:
        response["detached"] = f.read()
    if (working_dir / AbstractSigner.CLEARSIGNED_FILE).exists():
        with open(working_dir / AbstractSigner.CLEARSIGNED_FILE, "r") as f:
            response["clearsigned"] = f.read()
    util.shred_working_dir(working_dir)
    redis.delete(working_dir_key)
    return response
