import pytest
from httpx import AsyncClient

from app.core.models import Role

from .utils import assert_expected_response

# This marks all tests in the module as async.
pytestmark = pytest.mark.asyncio


async def test_roles_orphans_cleanup(async_client: AsyncClient, orphan_api, account):
    response = await async_client.post("/api/v4/orphans/cleanup/")
    status_code = 200 if account.role == Role.Package_Admin else 403
    assert_expected_response(response, status_code, orphan_api.cleanup)
