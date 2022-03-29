import logging

from enum import Enum
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from services.pulp import get_pulp_client

router = APIRouter()
logger = logging.getLogger(__name__)

class RepoTypeEnum(str, Enum):
    apt = "apt"
    yum = "yum"


class Repository(BaseModel):
    name: str
    type: RepoTypeEnum


@router.get("/repositories/")
async def list_repos() -> Any:
    logger.info("GET /repositories")
    async with get_pulp_client() as pulp_client:
        resp = await pulp_client.get("/repositories/")
        return resp.json()


@router.post("/repositories/")
async def create_repository(repo: Repository) -> Any:
    logger.info("POST /repositories")
    # TODO: better way to construct paths?
    if repo.type == "yum":
        path = "/repositories/rpm/rpm/"
    elif repo.type == "apt":
        path = "/repositories/deb/apt/"

    async with get_pulp_client() as pulp_client:
        resp = await pulp_client.post(path, json={"name": repo.name})
        return resp.json()
