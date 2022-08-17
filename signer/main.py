import json
import logging
import signer

from fastapi import BackgroundTasks, FastAPI, Request, Response, UploadFile
from pathlib import Path
from redis import Redis
from typing import Dict, Optional
from uuid import uuid4

app = FastAPI()
redis = Redis(host='localhost')
log = logging.getLogger('uvicorn')
pending = 'Pending'
done = 'Done'
failure = 'Failure'


def handle_request(unsigned_file: UploadFile, key_id: str, task_id: str):
    '''
    Handles signing of uploaded artifacts
    '''
    # Locking unnecessary; Pulp does this for us.
    log.info(f'Processing request for {task_id}, {key_id}')
    # Get Spooled Temporary File that represents our file in memory
    spooled_file = unsigned_file.file
    # TODO pass task_id
    if signer.sign_request(spooled_file, key_id, task_id):
        log.info(f'Successfully processed request for {task_id}')
        redis.set(task_id, done)
    else:
        log.error(f'FAILED request for {task_id}')
        redis.set(task_id, failure)


@app.post('/sign')
async def sign(background_tasks: BackgroundTasks,
               key_id: Optional[str],
               file: UploadFile) -> Dict:
    
    task_id = str(uuid4())
    redis.set(task_id, pending)
    background_tasks.add_task(handle_request, file, key_id, task_id)
    log.info(f'Received signing request with task ID {task_id} and key ID {key_id}')
    return {'x-ms-workflow-run-id': task_id}


@app.get('/signature', status_code=200)
async def signature(background_tasks: BackgroundTasks,
               task_id: str,
               response: Response) -> Dict:
    if not redis.exists(task_id):
        log.info(f'Request {task_id} does not exist')
        response.status_code = 400
        return
    request_status = redis.get(task_id)
    if request_status == bytes(pending, 'utf-8'):
        # Still working
        log.info(f'Request {task_id} is still pending')
        response.status_code = 204
        return
    if request_status == bytes(done, 'utf-8'):
        # Done
        return signer.get_signature_file(task_id)
    # Unknown request
    response.status_code = 400
