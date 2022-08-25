from datetime import datetime
from random import choice
from typing import Any, Dict, List, Optional, Union
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
    if type == RepoType.apt:
        return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=type, release="jammy")
    else:
        return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=type)


def gen_pulp_repo_response(type: RepoType, name: str) -> Dict[str, Any]:
    if type == RepoType.apt:
        id = f"repositories-deb-apt-{uuid4()}"
    else:
        id = f"repositories-rpm-rpm-{uuid4()}"
    return {"id": id, "pulp_created": datetime.now(), "name": name}


def gen_release_attrs() -> Dict[str, Union[str, List[str]]]:
    return dict(
        distribution=f"pmc_cli_test_release_{uuid4()}",
        codename="cortoso",
        suite="stable",
        components=["main", "contrib", "non-free"],
        architectures=["arm", "amd64"],
    )


def gen_distro_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_distro_{uuid4()}",
        type=DistroType.apt,
        base_path=f"{uuid4()}/{uuid4()}",
    )


def assert_expected_response(
    response: Response,
    expected_status_code: int,
    api_method: AsyncMock,
    expected_num_list_items: Optional[int] = None,
) -> None:
    __tracebackhide__ = True
    if response.status_code != expected_status_code:
        pytest.fail(f"Expected status {expected_status_code} but received {response.status_code}!")
    if expected_status_code % 100 == 2 and api_method.call_count != 1:
        pytest.fail(
            "Expected api_method to be called once but was instead called "
            f"{api_method.call_count} times!"
        )
    if expected_num_list_items:
        body = response.json()
        if not isinstance(body, type([])) and len(body) != expected_num_list_items:
            pytest.fail(
                f"Expected to return a list of {expected_num_list_items} items but instead"
                f"received {body}"
            )
