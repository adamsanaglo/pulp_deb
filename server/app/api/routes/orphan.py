from typing import Any, Optional

from fastapi.requests import Request
from fastapi import APIRouter
from fastapi_microsoft_identity import requires_auth

from services.pulp.api import OrphanApi

router = APIRouter()


@router.post("/orphans/cleanup/")
@requires_auth
async def cleanup_orphans(request: Request, protection_time: Optional[int] = None) -> Any:
    async with OrphanApi() as api:
        return await api.cleanup(protection_time)
