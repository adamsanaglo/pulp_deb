from typing import Any, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.sql.selectable import Select

from app.core.db import AsyncSession, get_session
from app.core.models import Account
from app.core.schemas import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
    Pagination,
)

router = APIRouter()


async def _get_list(
    session: AsyncSession, query: Select, limit: int, offset: int
) -> Tuple[List[Any], int]:
    """Takes a query and returns a page of results and count of total results."""
    count_query = select(func.count()).select_from(query.subquery())
    count = (await session.exec(count_query)).scalar_one()

    query = query.limit(limit).offset(offset)
    results = (await session.exec(query)).scalars().all()

    return results, count


@router.get("/accounts/")
async def list_account(
    pagination: Pagination = Depends(Pagination),
    session: AsyncSession = Depends(get_session),
    name: Optional[str] = None,
    name__contains: Optional[str] = None,
    name__icontains: Optional[str] = None,
    ordering: Optional[str] = None,
) -> AccountListResponse:
    query = select(Account)
    if name:
        query = query.where(Account.name == name)
    if name__contains:
        query = query.where(Account.name.contains(name__contains))
    if name__icontains:
        query = query.where(Account.name.ilike(f"%{name__icontains}%"))

    if ordering:
        if ordering.startswith("-"):
            query = query.order_by(getattr(Account, ordering[1:]).desc())
        else:
            query = query.order_by(getattr(Account, ordering))

    accounts, count = await _get_list(session, query, **pagination.dict())
    return AccountListResponse(count=count, results=accounts, **pagination.dict())


@router.post("/accounts/")
async def add_account(
    account_data: AccountCreate, session: AsyncSession = Depends(get_session)
) -> AccountResponse:
    account = Account(**account_data.dict())
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/accounts/{id}/")
async def read_account(id: UUID, session: AsyncSession = Depends(get_session)) -> AccountResponse:
    account = await session.get(Account, id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/accounts/{id}/")
async def update_account(
    id: UUID, account: AccountUpdate, session: AsyncSession = Depends(get_session)
) -> AccountResponse:
    db_account = await session.get(Account, id)
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, val in account.dict(exclude_unset=True).items():
        setattr(db_account, key, val)
    session.add(db_account)
    await session.commit()
    await session.refresh(db_account)
    return db_account


@router.delete("/accounts/{id}/", status_code=204)
async def delete_account(id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    account = await session.get(Account, id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await session.delete(account)
    await session.commit()
