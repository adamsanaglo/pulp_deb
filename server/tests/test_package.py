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
        "/api/v4/packages/",
        params={"ignore_signature": True},
        files={"file": ("test.rpm", b"x")},
    )
    expected_status = 200 if account.role in (Role.Package_Admin, Role.Publisher) else 403
    assert_expected_response(response, expected_status, package_api.create)


async def test_file_type(async_client: AsyncClient, package_api):
    response = await async_client.post(
        "/api/v4/packages/",
        params={"ignore_signature": True},
        files={"file": ("test.bad", b"x")},
    )
    assert_expected_response(response, 422, package_api.create)  # automatic file detection fails

    response = await async_client.post(
        "/api/v4/packages/",
        params={"ignore_signature": True, "file_type": "file"},
        files={"file": ("test.bad", b"x")},
    )
    assert_expected_response(response, 200, package_api.create)


async def test_roles_package_read(async_client: AsyncClient, package_api, account):
    response = await async_client.get(f"/api/v4/packages/content-deb-packages-{uuid4()}/")
    assert_expected_response(response, 200, package_api.read)
