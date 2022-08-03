import datetime
import json
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import azure.functions as func


class mirror_status:
    """Class for encapsulating mirror status."""

    def __init__(self, mirror_url: str):
        """Initialize class with a mirror url."""
        self.mirror_url = mirror_url
        self.running = True
        self.errors: list[str] = []
        self.time = str(datetime.datetime.utcnow())

    def add_error(self, error: str):
        """Add and log an error."""
        logging.error(f"Mirror error for {self.mirror_url}: {error}")
        self.errors.append(error)
        self.running = False

    def to_dict(self) -> dict:
        """Construct and return a dictionary representation of the mirror status."""
        entry = {
            self.mirror_url: {
                "running": self.running,
                "errors": self.errors,
                "time": self.time
            }
        }
        return entry


def urljoin(*paths: str) -> str:
    """Join together a set of url components."""
    # urllib's urljoin has a few gotchas and doesn't handle multiple paths
    return "/".join(map(lambda path: path.strip("/"), paths))


def retry_session(retries: int = 5, backoff_factor: float = 0.5) -> requests.Session:
    """Create a requests.Session with retries and exponential backoff."""
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_url(
    url: str,
    stream: bool = False,
    session: Optional[requests.Session] = None,
    timeout=10
) -> requests.Response:
    """
    Call requests.get() on a url and return the requests.Response. By default,
    this function will handle retries with exponential backoff and raise
    request.exception.HTTPError if anything goes wrong.
    """
    if not session:
        session = retry_session()
    resp = session.get(url, stream=stream, timeout=timeout)
    resp.raise_for_status()
    return resp


def log_message(msg: func.QueueMessage) -> None:
    """Log message content and information."""
    logging.info(json.dumps({
        'id': msg.id,
        'body': msg.get_body().decode('utf-8'),
        'expiration_time': (msg.expiration_time.isoformat()
                            if msg.expiration_time else None),
        'insertion_time': (msg.insertion_time.isoformat()
                           if msg.insertion_time else None),
        'time_next_visible': (msg.time_next_visible.isoformat()
                              if msg.time_next_visible else None),
        'pop_receipt': msg.pop_receipt,
        'dequeue_count': msg.dequeue_count
    }))


def get_status_msg(status: dict, status_type: str) -> str:
    """Get the status message to add to the results-queue."""
    output = dict()
    output["status_type"] = status_type
    output["status"] = status
    return json.dumps(output, indent=4)
