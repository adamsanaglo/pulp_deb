import esrp
import logging
from redis import Redis

from azure.core.exceptions import ClientAuthenticationError
from config import is_valid_keycode
from retrying import retry
from tempfile import SpooledTemporaryFile
from typing import Dict

redis = Redis(host='localhost')
log = logging.getLogger('uvicorn')


def get_signature_index(task_id: str):
    """
    Just a convenience method for determining the redis key that
    holds the signature for a given request.
    """
    return f'{task_id}_signature'


def sign_request(unsigned_file: SpooledTemporaryFile, key_id: str, task_id: str) -> bool:
    '''
    Write the unsigned file to disk
    Submit it to ESRP for signing
    Store the signature for return to the requestor
    '''
    if key_id == "legacy":
        # TODO Implement legacy signing
        log.error('Legacy signing not yet supported')
        return False
    if not is_valid_keycode(key_id):
        log.error(f'Key code {key_id} is not in the list of supported keys for task [{task_id}]')
    try:
        return sign_request_retriable(unsigned_file, task_id, key_id)
    except Exception as e:
        log.error(f'Fatal error to handle request for {task_id}: {e}')
        return False


@retry(stop_max_attempt_number=10, wait_exponential_multiplier=1000, wait_exponential_max=60000)
def sign_request_retriable(unsigned_file: SpooledTemporaryFile, task_id: str, key_id: str) -> bool:
    '''
    Retry the request up to 10 times with exponential backoff
    '''
    try:
        log.info(f'Generating signature for {task_id}')
        # Sign content
        dst_file = esrp.sign_content(unsigned_file, esrp.SigningOperation.detached, key_id)
        signature_key = get_signature_index(task_id)
        log.info(f'Successfully signed file for {task_id}')
        redis.set(signature_key, dst_file)
        return True
    except (esrp.ESRPAuthException, ValueError, ClientAuthenticationError) as e:
        # Non-retriable errors
        log.error(f'[{type(e)}] Fatal error handling request for task [{task_id}]: {e}')
        return False
    except Exception as e:
        # Re-raise exception, which will trigger retry logic.
        log.error(f'[{type(e)}] Retriable error handling request for task [{task_id}]: {e}')
        raise


def get_signature_file(task_id: str) -> Dict:
    """
    Generate a Dict containing the signature for the specified task id
    """
    response = {
        "content": ""
    }
    signature_key = get_signature_index(task_id)
    if not redis.exists(signature_key):
        log.error(f'Key {signature_key} not present in Redis')
        return Response
    sig_file = redis.get(signature_key).decode('utf-8')
    with open(sig_file, 'r') as f:
        response["content"] = f.read()
    return response