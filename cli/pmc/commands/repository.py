import json
from enum import Enum

import typer

from pmc.client import client

app = typer.Typer()


class RepoTypeEnum(str, Enum):
    apt = "apt"
    yum = "yum"


@app.command()
def list() -> None:
    r = client.get("/repositories/")
    typer.secho(json.dumps(r.json(), indent=3))


@app.command()
def create(name: str, repo_type: RepoTypeEnum) -> None:
    data = {"name": name, "type": repo_type}
    r = client.post("/repositories/", json=data)
    typer.secho(json.dumps(r.json(), indent=3))
