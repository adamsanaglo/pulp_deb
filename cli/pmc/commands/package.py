import json

import typer

from pmc.client import client

app = typer.Typer()


@app.command()
def list() -> None:
    r = client.get("/packages/")
    typer.secho(json.dumps(r.json(), indent=3))


@app.command()
def upload(file: typer.FileBinaryRead) -> None:
    files = {"file": file}
    r = client.post("/packages/", files=files)
    typer.secho(json.dumps(r.json(), indent=3))
