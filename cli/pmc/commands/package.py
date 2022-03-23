import typer

from pmc.client import client
from pmc.utils import output_response

app = typer.Typer()


@app.command()
def list() -> None:
    r = client.get("/packages/")
    output_response(r)


@app.command()
def upload(file: typer.FileBinaryRead) -> None:
    files = {"file": file}
    r = client.post("/packages/", files=files)
    output_response(r)
