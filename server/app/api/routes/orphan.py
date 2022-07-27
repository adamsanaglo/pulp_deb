from typing import Any, Optional

from fastapi import APIRouter

from app.core.schemas import TaskResponse
from app.services.pulp.api import OrphanApi

router = APIRouter()


@router.post("/orphans/cleanup/", response_model=TaskResponse)
async def cleanup_orphans(protection_time: Optional[int] = None) -> Any:
    async with OrphanApi() as api:
        return await api.cleanup(protection_time)
