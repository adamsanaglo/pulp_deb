from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import assert_expected_response

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("type", ("deb", "rpm"))
async def test_roles_package_list(async_client: AsyncClient, package_api, account, type):
    response = await async_client.get(f"/api/v4/{type}/packages/")
    assert_expected_response(response, 200, package_api.list)


async def test_roles_package_create(async_client: AsyncClient, package_api, account):
    response = await async_client.post(
        "/api/v4/packages/", params={"ignore_signature": True}, files={"file": b"x"}
    )
    expected_status = 200 if account.role in (Role.Package_Admin, Role.Publisher) else 403
    assert_expected_response(response, expected_status, package_api.create)


async def test_roles_package_read(async_client: AsyncClient, package_api, account):
    response = await async_client.get(f"/api/v4/packages/content-deb-packages-{uuid4()}/")
    assert_expected_response(response, 200, package_api.read)
