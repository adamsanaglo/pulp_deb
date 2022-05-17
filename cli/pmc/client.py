import httpx


def _raise_for_status(response: httpx.Response) -> None:
    response.read()  # read the response's body before raise_for_status closes it
    response.raise_for_status()


# TODO: load configuration and close() client
client = httpx.Client(
    base_url="http://localhost:8000/api/v4",
    event_hooks={"response": [_raise_for_status]},
)
