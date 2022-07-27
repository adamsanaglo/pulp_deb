from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import assert_expected_response

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_task_list(async_client: AsyncClient, task_api, account):
    response = await async_client.get("/api/v4/tasks/")
    assert_expected_response(response, 200, task_api.list)


async def test_roles_task_read(async_client: AsyncClient, task_api, account):
    response = await async_client.get(f"/api/v4/tasks/tasks-{uuid4()}/")
    assert_expected_response(response, 200, task_api.read)


async def test_roles_task_cancel(async_client: AsyncClient, task_api, account):
    response = await async_client.patch(f"/api/v4/tasks/tasks-{uuid4()}/cancel/")
    status_code = 200 if account.role == Role.Account_Admin else 403
    assert_expected_response(response, status_code, task_api.cancel)
