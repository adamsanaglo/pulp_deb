from typing import Any

from fastapi.requests import Request
from fastapi import APIRouter, Depends, HTTPException
from fastapi_microsoft_identity import requires_auth

from core.schemas import Pagination, TaskId
from services.pulp.api import TaskApi, TaskCancelException

router = APIRouter()


@router.get("/tasks/")
@requires_auth
async def list_tasks(request: Request, pagination: Pagination = Depends(Pagination)) -> Any:
    async with TaskApi() as api:
        return await api.list(pagination)


@router.get("/tasks/{id}/")
@requires_auth
async def show_task(request: Request, id: TaskId) -> Any:
    async with TaskApi() as api:
        return await api.read(id)


@router.patch("/tasks/{id}/cancel/")
@requires_auth
async def cancel_task(request: Request, id: TaskId) -> Any:
    async with TaskApi() as api:
        try:
            return await api.cancel(id)
        except TaskCancelException:
            raise HTTPException(status_code=409, detail=f"Cannot cancel task '{id}'.")
