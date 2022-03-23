from enum import Enum

import typer

from pmc.client import client
from pmc.utils import output_response

app = typer.Typer()


class RepoTypeEnum(str, Enum):
    apt = "apt"
    yum = "yum"


@app.command()
def list() -> None:
    r = client.get("/repositories/")
    output_response(r)


@app.command()
def create(name: str, repo_type: RepoTypeEnum) -> None:
    data = {"name": name, "type": repo_type}
    r = client.post("/repositories/", json=data)
    output_response(r)
