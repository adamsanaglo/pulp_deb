from random import choice
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import Response

from app.core.models import Role
from app.core.schemas import DistroType, RepoType


def gen_account_attrs(role: Role = Role.Publisher) -> Dict[str, Any]:
    my_uuid = uuid4()
    return dict(
        id=str(my_uuid),
        name=f"pmc_cli_test_account_{my_uuid}",
        contact_email="alice@contoso.com;bob@contoso.com",
        icm_service="test_icm_service",
        icm_team="test_icm_team",
        role=str(role),
        is_enabled=True,
    )


def gen_repo_attrs(type: Optional[RepoType] = None) -> Dict[str, str]:
    if not type:
        type = choice([RepoType.apt, RepoType.yum])
    return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=type)


def gen_distro_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_distro_{uuid4()}",
        type=DistroType.apt,
        base_path=f"{uuid4()}/{uuid4()}",
    )


def assert_expected_response(
    response: Response, expected_status_code: int, api_method: AsyncMock
) -> None:
    __tracebackhide__ = True
    if response.status_code != expected_status_code:
        pytest.fail(f"Expected status {expected_status_code} but received {response.status_code}!")
    if expected_status_code % 100 == 2 and api_method.call_count != 1:
        pytest.fail(
            "Expected api_method to be called once but was instead called "
            f"{api_method.call_count} times!"
        )
