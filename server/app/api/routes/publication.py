import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends

from app.core.schemas import PackageId, Pagination, PublicationId
from app.services.pulp.api import PublicationApi

router = APIRouter()
logger = logging.getLogger(__name__)

# TODO: define the response model for publication


@router.get("/publications/")
async def list(
    pagination: Pagination = Depends(Pagination),
    repository: Optional[str] = None,
    package: Optional[PackageId] = None,
) -> Any:
    params = dict(repository=repository, content=package)

    return await PublicationApi.list(
        pagination,
        params=params,
    )


@router.get("/publications/{id}/")
async def read(id: PublicationId) -> Any:
    return await PublicationApi.read(id)


@router.delete("/publications/{id}/", status_code=204)
async def delete(id: PublicationId) -> Any:
    await PublicationApi.destroy(id)
