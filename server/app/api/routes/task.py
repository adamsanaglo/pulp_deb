from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import requires_account_admin
from app.core.schemas import Pagination, TaskId, TaskListResponse, TaskQuery, TaskReadResponse
from app.services.pulp.api import TaskApi, TaskCancelException

router = APIRouter()


@router.get("/tasks/")
async def list_tasks(
    params: TaskQuery = Depends(TaskQuery),
    pagination: Pagination = Depends(Pagination),
) -> TaskListResponse:
    return await TaskApi.list(pagination, params.dict(exclude_none=True))


@router.get("/tasks/{id}/")
async def read_task(id: TaskId) -> TaskReadResponse:
    return await TaskApi.read(id)


@router.patch("/tasks/{id}/cancel/", dependencies=[Depends(requires_account_admin)])
async def cancel_task(id: TaskId) -> TaskReadResponse:
    try:
        return await TaskApi.cancel(id)
    except TaskCancelException:
        raise HTTPException(status_code=409, detail=f"Cannot cancel task '{id}'.")
