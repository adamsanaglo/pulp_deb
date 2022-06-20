from typing import Any, Optional

from fastapi import APIRouter

from services.pulp.api import OrphanApi

router = APIRouter()


@router.post("/orphans/cleanup/")
async def cleanup_orphans(protection_time: Optional[int] = None) -> Any:
    async with OrphanApi() as api:
        return await api.cleanup(protection_time)
