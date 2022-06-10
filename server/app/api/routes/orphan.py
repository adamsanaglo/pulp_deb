from typing import Any

from fastapi import APIRouter

from services.pulp.api import OrphanApi

router = APIRouter()


@router.post("/orphans/cleanup/")
async def cleanup_orphans() -> Any:
    async with OrphanApi() as api:
        return await api.cleanup()
