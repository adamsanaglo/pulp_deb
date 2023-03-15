import json
import logging
import os
import tempfile
from pathlib import Path

import azure.functions as func
import httpx

ICM_URL = os.getenv("ICM_URL", "")
RG = os.getenv("resourceGroup", "")
CLEAR_DEADLETTER = os.getenv("clearDeadletter", False)
if os.getenv("MSAL_CERT_PATH"):
    MSAL_CERT = Path(os.environ["MSAL_CERT_PATH"]).expanduser().read_text()
else:
    MSAL_CERT = os.environ["MSAL_CERT"]

TSG_URL = (
    "https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/_layouts/15/Doc.aspx?sourcedoc="
    "{35e507ad-15a7-434a-9a81-e1e296827e79}&action=view&wd=target%28TSGs.one%7C141d6d0f-3f3"
    "b-4599-8b63-2a78840930c5%2FAzure%20Migration%20Functions%7C4bf848f4-d160-45f1-a6af-7da"
    "4b2e84593%2F%29&wdorigin=NavigationUrl"
)
ICM_BODY = (
    "A migration message failed in %s, this can cause PMC vCurrent and vNext to become out-of-sync!"
    '<br><a href="%s">See the TSG.</a><br><br><br>%s'
)


def main(inMsg: func.ServiceBusMessage, outMsg: func.Out[str]):
    """
    If a message is dead-lettered in the pmcmigrate queue, file an ICM and transfer it to an
    "already-alerted" queue.
    """
    msg_json = inMsg.get_body().decode("utf-8")
    msg = json.loads(msg_json)
    if "-ppe-" in RG:
        environment = "ppe"
    elif "-prod-" in RG:
        environment = "prod"
    else:
        environment = "tux-dev"

    title = f"PMC Migration Message Failure in {environment}: {inMsg.message_id}"
    correlation_id = msg.get("correlation_id", "")
    body = ICM_BODY % (environment, TSG_URL, msg_json)
    request = {"title": title, "correlation_id": correlation_id, "body": body}

    if ICM_URL and MSAL_CERT and not CLEAR_DEADLETTER:
        logging.info(f"New dead-letter message, filing ICM: {request}")
        # httpx only accepts certs in the form of a path to the on-disk pem.
        # https://github.com/encode/httpx/issues/924#issuecomment-1052681712
        with tempfile.TemporaryFile(mode="w") as f:
            f.write(MSAL_CERT)
            f.flush()
            # NamedTemporaryFile leaves the file linked where other processes can theoretically
            # find it on the filesystem. TemporaryFile unlinks the file immediately, and then we
            # can just pass the path to the file descriptor to httpx.
            filename = f"/proc/{os.getpid()}/fd/{f.name}"
            response = httpx.post(ICM_URL, cert=filename, json=request, timeout=60)
        response.raise_for_status()
    else:
        logging.info(
            "New dead-letter message, ICM filing not enabled in this environment. "
            f"Would have filed: {request}"
        )

    if not CLEAR_DEADLETTER:
        outMsg.set(msg_json)
