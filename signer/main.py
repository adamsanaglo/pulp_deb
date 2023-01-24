from typing import Dict
from uuid import uuid4

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import BackgroundTasks, FastAPI, Response, UploadFile
from redis import Redis

import signer
from config import log

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
redis = Redis(host="localhost")
PENDING = "Pending"
DONE = "Done"
FAILURE = "Failure"


def handle_request(file: UploadFile, clearsign: bool, key_id: str, task_id: str):
    """
    This method will run in the background and signal status when it is complete.
    """
    # Locking unnecessary; Pulp does this for us.
    log.info(f"Processing request for {task_id}, {key_id}")
    # Get Spooled Temporary File that represents our file in memory
    if signer.sign_request(file.file, clearsign, key_id, task_id):
        log.info(f"Successfully processed request for {task_id}")
        redis.set(task_id, DONE)
    else:
        log.error(f"FAILED request for {task_id}")
        redis.set(task_id, FAILURE)


@app.post("/sign")
async def sign(
    background_tasks: BackgroundTasks, clearsign: bool, key_id: str, file: UploadFile
) -> Dict:
    """
    Request a signature, which will be processed in the background.
    Required params:
    clearsign: Whether or not to also do a clearsign signature.
    key_id: ("legacy"|"CP-450778-Pgp"(in PPE)|"CP-450779-Pgp"(in tux-dev/prod)) Which key to use.
    """
    task_id = str(uuid4())
    redis.set(task_id, PENDING)
    background_tasks.add_task(handle_request, file, clearsign, key_id, task_id)
    log.info(f"Received signing request with task ID {task_id} and key ID {key_id}")
    return {"x-ms-workflow-run-id": task_id}


@app.get("/signature", status_code=200)
async def signature(task_id: str, response: Response) -> Response:
    """
    Get the signed file(s). Depending on the type of signature requested may include the following:
    {
        "detached": UTF-8 encoded detached signature,
        "clearsigned": [Optional] UTF-8 encoded clearsigned signature.
    }
    """
    response.status_code = 400
    request_status = redis.get(task_id)
    if request_status is None:
        log.info(f"Request {task_id} does not exist")
    elif request_status == bytes(PENDING, "utf-8"):
        # Still working
        log.info(f"Request {task_id} is still pending")
        response.status_code = 204
    elif request_status == bytes(DONE, "utf-8"):
        # Done
        log.info(f"Request {task_id} is done")
        response.status_code = 200
        redis.delete(task_id)
        return signer.get_signature_file(task_id)

    return response


@app.get("/status", status_code=200)
async def status() -> Dict:
    num = len(redis.keys("*"))
    return {"Computer?": "idle" if not num else num}
