from typing import Any

from fastapi import APIRouter

from core.schemas import TaskId
from services.pulp.api import TaskApi

router = APIRouter()


@router.get("/tasks/")
async def list_tasks() -> Any:
    async with TaskApi() as api:
        return await api.list()


@router.get("/tasks/{id}/")
async def show_task(id: TaskId) -> Any:
    async with TaskApi() as api:
        return await api.read(id)
