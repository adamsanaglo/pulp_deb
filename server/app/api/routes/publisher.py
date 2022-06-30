from typing import Any, List, Tuple

from fastapi.requests import Request
from fastapi import APIRouter, Depends, HTTPException
from fastapi_microsoft_identity import requires_auth
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.selectable import Select

from core.db import get_session
from core.models import Publisher
from core.schemas import (
    Pagination,
    PublisherCreate,
    PublisherId,
    PublisherListResponse,
    PublisherResponse,
    PublisherUpdate,
)

router = APIRouter()


async def _get_list(
    session: AsyncSession, query: Select, limit: int, offset: int
) -> Tuple[List[Any], int]:
    """Takes a query and returns a list of results and total count."""
    count_query = select(func.count()).select_from(query.subquery())
    count = (await session.execute(count_query)).scalar_one()

    query = query.limit(limit).offset(offset)
    results = (await session.execute(query)).scalars().all()

    return results, count


@router.get("/publishers/", response_model=PublisherListResponse)
@requires_auth
async def list_publishers(
    request: Request, pagination: Pagination = Depends(Pagination),
    session: AsyncSession = Depends(get_session)
) -> PublisherListResponse:
    query = select(Publisher)
    publishers, count = await _get_list(session, query, **pagination.dict())
    return PublisherListResponse(count=count, results=publishers, **pagination.dict())


@router.post("/publishers/", response_model=PublisherResponse)
@requires_auth
async def add_publisher(
    request: Request, publisher_data: PublisherCreate, session: AsyncSession = Depends(get_session)
) -> Publisher:
    publisher = Publisher(**publisher_data.dict())
    session.add(publisher)
    await session.commit()
    await session.refresh(publisher)
    return publisher


@router.get("/publishers/{id}/", response_model=PublisherResponse)
@requires_auth
async def read_publisher(
   request: Request, id: PublisherId, session: AsyncSession = Depends(get_session)
) -> Publisher:
    publisher = await session.get(Publisher, id.uuid)
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return publisher


@router.patch("/publishers/{id}/", response_model=PublisherResponse)
@requires_auth
async def update_publisher(
    request: Request, id: PublisherId, publisher: PublisherUpdate, session: AsyncSession = Depends(get_session)
) -> Publisher:
    db_publisher = await session.get(Publisher, id.uuid)
    if not db_publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    for key, val in publisher.dict(exclude_unset=True).items():
        setattr(db_publisher, key, val)
    session.add(db_publisher)
    await session.commit()
    await session.refresh(db_publisher)
    return db_publisher


@router.delete("/publishers/{id}/", status_code=204)
@requires_auth
async def delete_publisher(request: Request, id: PublisherId, session: AsyncSession = Depends(get_session)) -> None:
    publisher = await session.get(Publisher, id.uuid)
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    await session.delete(publisher)
    await session.commit()
