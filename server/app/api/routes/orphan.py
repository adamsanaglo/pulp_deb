from typing import Optional

from fastapi import APIRouter

from app.core.schemas import TaskResponse
from app.services.pulp.api import OrphanApi

router = APIRouter()


@router.post("/orphans/cleanup/")
async def cleanup_orphans(protection_time: Optional[int] = None) -> TaskResponse:
    return await OrphanApi.cleanup(protection_time)
