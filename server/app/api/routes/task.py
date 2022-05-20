from typing import Any

from fastapi import APIRouter, HTTPException

from core.schemas import TaskId
from services.pulp.api import TaskApi, TaskCancelException

router = APIRouter()


@router.get("/tasks/")
async def list_tasks() -> Any:
    async with TaskApi() as api:
        return await api.list()


@router.get("/tasks/{id}/")
async def show_task(id: TaskId) -> Any:
    async with TaskApi() as api:
        return await api.read(id)


@router.patch("/tasks/{id}/cancel/")
async def cancel_task(id: TaskId) -> Any:
    async with TaskApi() as api:
        try:
            return await api.cancel(id)
        except TaskCancelException:
            raise HTTPException(status_code=409, detail=f"Cannot cancel task '{id}'.")
