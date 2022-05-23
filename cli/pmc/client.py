from contextlib import contextmanager
from typing import Generator

import httpx

from .schemas import Config


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    response.raise_for_status()


@contextmanager
def get_client(config: Config) -> Generator[httpx.Client, None, None]:
    client = httpx.Client(
        base_url=config.base_url,
        event_hooks={"response": [_raise_for_status]},
    )
    try:
        yield client
    finally:
        client.close()
