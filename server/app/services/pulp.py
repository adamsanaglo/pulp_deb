from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from core.config import settings


@asynccontextmanager
async def get_pulp_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    pulp_client = httpx.AsyncClient(
        base_url=f"{settings.PULP_HOST}{settings.PULP_API_PATH}",
        auth=(settings.PULP_USERNAME, settings.PULP_PASSWORD),
    )
    try:
        yield pulp_client
    finally:
        await pulp_client.aclose()
