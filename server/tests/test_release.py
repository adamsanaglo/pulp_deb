from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import assert_expected_response, gen_release_attrs

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_repository_list(async_client: AsyncClient, release_api, account):
    response = await async_client.get(
        f"/api/v4/repositories/repositories-deb-apt-{uuid4()}/releases/"
    )
    assert_expected_response(response, 200, release_api.list)


async def test_roles_repository_create(async_client: AsyncClient, release_api, account):
    response = await async_client.post(
        f"/api/v4/repositories/repositories-deb-apt-{uuid4()}/releases/", json=gen_release_attrs()
    )
    expected_status_code = 200 if account.role == Role.Repo_Admin else 403
    assert_expected_response(response, expected_status_code, release_api.create)
