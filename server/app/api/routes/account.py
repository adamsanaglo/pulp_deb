from typing import Any, List, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.selectable import Select

from core.db import get_session
from core.models import Account
from core.schemas import (
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
    count = (await session.execute(count_query)).scalar_one()

    query = query.limit(limit).offset(offset)
    results = (await session.execute(query)).scalars().all()

    return results, count


@router.get("/accounts/", response_model=AccountListResponse)
async def list_account(
    pagination: Pagination = Depends(Pagination), session: AsyncSession = Depends(get_session)
) -> AccountListResponse:
    query = select(Account)
    accounts, count = await _get_list(session, query, **pagination.dict())
    return AccountListResponse(count=count, results=accounts, **pagination.dict())


@router.post("/accounts/", response_model=AccountResponse)
async def add_account(
    account_data: AccountCreate, session: AsyncSession = Depends(get_session)
) -> Account:
    account = Account(**account_data.dict())
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/accounts/{id}/", response_model=AccountResponse)
async def read_account(id: UUID, session: AsyncSession = Depends(get_session)) -> Account:
    account = await session.get(Account, id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/accounts/{id}/", response_model=AccountResponse)
async def update_account(
    id: UUID, account: AccountUpdate, session: AsyncSession = Depends(get_session)
) -> Account:
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
