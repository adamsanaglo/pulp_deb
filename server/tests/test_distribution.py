from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import assert_expected_response, gen_distro_attrs

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_distribution_list(async_client: AsyncClient, distribution_api, account):
    response = await async_client.get("/api/v4/distributions/")
    assert_expected_response(response, 200, distribution_api.list)


async def test_roles_distribution_create(async_client: AsyncClient, distribution_api, account):
    response = await async_client.post("/api/v4/distributions/", json=gen_distro_attrs())
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, distribution_api.create)


async def test_roles_distribution_read(async_client: AsyncClient, distribution_api, account):
    response = await async_client.get(f"/api/v4/distributions/distributions-deb-apt-{uuid4()}/")
    assert_expected_response(response, 200, distribution_api.read)


async def test_roles_distribution_update(async_client: AsyncClient, distribution_api, account):
    response = await async_client.patch(
        f"/api/v4/distributions/distributions-deb-apt-{uuid4()}/", json={"name": "test"}
    )
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, distribution_api.update)


async def test_roles_distribution_delete(async_client: AsyncClient, distribution_api, account):
    response = await async_client.delete(f"/api/v4/distributions/distributions-deb-apt-{uuid4()}/")
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, distribution_api.destroy)
