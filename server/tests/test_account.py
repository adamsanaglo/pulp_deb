import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import gen_account_attrs

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_account_list(async_client: AsyncClient, account):
    response = await async_client.get("/api/v4/accounts/")
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_account_add(async_client: AsyncClient, account):
    new_account = gen_account_attrs()
    response = await async_client.post("/api/v4/accounts/", json=new_account)
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_account_read(async_client: AsyncClient, db_session, account):
    db_session.add(account)
    response = await async_client.get(f"/api/v4/accounts/{account.id}/")
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_account_update(async_client: AsyncClient, db_session, account):
    db_session.add(account)
    response = await async_client.patch(f"/api/v4/accounts/{account.id}/", json={"name": "test"})
    assert response.status_code == (200 if account.role == Role.Account_Admin else 403)


async def test_roles_account_delete(async_client: AsyncClient, db_session, account):
    db_session.add(account)
    response = await async_client.delete(f"/api/v4/accounts/{account.id}/")
    assert response.status_code == (204 if account.role == Role.Account_Admin else 403)