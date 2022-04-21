from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.db import get_session
from core.models import Publisher
from core.schemas import PublisherCreate, PublisherId, PublisherResponse, PublisherUpdate

router = APIRouter()


@router.get("/publishers/", response_model=List[PublisherResponse])
async def list_publishers(session: AsyncSession = Depends(get_session)) -> List[Publisher]:
    result = await session.execute(select(Publisher))
    publishers = result.scalars().all()
    return publishers


@router.post("/publishers/", response_model=PublisherResponse)
async def add_publisher(
    publisher_data: PublisherCreate, session: AsyncSession = Depends(get_session)
) -> Publisher:
    publisher = Publisher(**publisher_data.dict())
    session.add(publisher)
    await session.commit()
    await session.refresh(publisher)
    return publisher


@router.get("/publishers/{id}/", response_model=PublisherResponse)
async def read_publisher(
    id: PublisherId, session: AsyncSession = Depends(get_session)
) -> Publisher:
    publisher = await session.get(Publisher, id.uuid)
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return publisher


@router.patch("/publishers/{id}/", response_model=PublisherResponse)
async def update_publisher(
    id: PublisherId, publisher: PublisherUpdate, session: AsyncSession = Depends(get_session)
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
async def delete_publisher(id: PublisherId, session: AsyncSession = Depends(get_session)) -> None:
    publisher = await session.get(Publisher, id.uuid)
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")
    await session.delete(publisher)
    await session.commit()
