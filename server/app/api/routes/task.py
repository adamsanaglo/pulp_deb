from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requires_account_admin
from app.core.schemas import Pagination, TaskId, TaskListResponse, TaskQuery, TaskReadResponse
from app.services.pulp.api import TaskApi, TaskCancelException

router = APIRouter()


@router.get("/tasks/", response_model=TaskListResponse)
async def list_tasks(
    params: TaskQuery = Depends(TaskQuery),
    pagination: Pagination = Depends(Pagination),
) -> Any:
    return await TaskApi.list(pagination, params.dict(exclude_none=True))


@router.get("/tasks/{id}/", response_model=TaskReadResponse)
async def read_task(id: TaskId) -> Any:
    return await TaskApi.read(id)


@router.patch(
    "/tasks/{id}/cancel/",
    response_model=TaskReadResponse,
    dependencies=[Depends(requires_account_admin)],
)
async def cancel_task(id: TaskId) -> Any:
    try:
        return await TaskApi.cancel(id)
    except TaskCancelException:
        raise HTTPException(status_code=409, detail=f"Cannot cancel task '{id}'.")
