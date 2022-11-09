from datetime import datetime
from random import choice
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import Response

from app.core.models import Role
from app.core.schemas import ContentId, DistroType, PackageId, RepoId, RepoType, RepoVersionId


def gen_account_attrs(role: Role = Role.Publisher) -> Dict[str, Any]:
    my_uuid = uuid4()
    return dict(
        oid=str(my_uuid),
        name=f"pmc_cli_test_account_{my_uuid}",
        contact_email="alice@contoso.com;bob@contoso.com",
        icm_service="test_icm_service",
        icm_team="test_icm_team",
        role=str(role),
        is_enabled=True,
    )


def gen_repo_attrs(type: Optional[RepoType] = None) -> Dict[str, Union[str, None]]:
    if not type:
        type = choice([RepoType.apt, RepoType.yum, RepoType.python, RepoType.file])
    if type == RepoType.apt:
        return dict(
            name=f"pmc_cli_test_repo_{uuid4()}",
            type=type,
            release="jammy",
            signing_service="legacy",
        )
    elif type == RepoType.yum:
        return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=type, signing_service="legacy")
    else:
        return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=type, signing_service=None)


def gen_pulp_repo_response(type: RepoType, name: str) -> Dict[str, Any]:
    repo_id = gen_repo_id(type)
    repo_version = RepoVersionId(f"{repo_id}-versions-2")
    return {
        "id": gen_repo_id(type),
        "pulp_created": datetime.now(),
        "name": name,
        "latest_version": repo_version,
    }


def gen_release_attrs() -> Dict[str, Union[str, List[str]]]:
    return dict(
        name=f"pmc_cli_test_release_{uuid4()}",
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


def gen_distro_read_attrs() -> Dict[str, str]:
    return dict(
        id=f"distributions-deb-apt-{uuid4()}",
        pulp_created="2022-10-4 17:23:00",
        name="",
        base_path="",
        base_url="",
    )


def gen_task_attrs() -> Dict[str, str]:
    return dict(task=f"tasks-{uuid4()}")


def gen_task_read_attrs() -> Dict[str, Any]:
    return dict(
        id=gen_task_attrs()["task"],
        pulp_created="2022-10-4 17:23:00",
        state="denial",
        name="Horton",
        logging_cid=uuid4(),
        created_resources=[],
        reserved_resources_record=[],
    )


def gen_list_attrs(my_list: List[Any]) -> Dict[str, Any]:
    return dict(
        count=len(my_list),
        limit=100,
        offset=0,
        results=my_list,
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


def gen_repo_id(type: RepoType) -> RepoId:
    if type == RepoType.apt:
        return RepoId(f"repositories-deb-apt-{uuid4()}")
    elif type == RepoType.yum:
        return RepoId(f"repositories-rpm-rpm-{uuid4()}")
    else:
        return RepoId(f"repositories-{type}-{type}-{uuid4()}")


def gen_package_id() -> PackageId:
    return PackageId(f"content-deb-packages-{uuid4()}")


def gen_package_attrs() -> Dict[str, str]:
    return dict(
        id=gen_package_id(),
        pulp_created="2022-10-4 17:23:00",
        sha256="",
        sha384="",
        sha512="",
        package="",
        version="",
        architecture="",
        relative_path="",
        maintainer="",
        description="",
    )


def gen_release_id() -> ContentId:
    return ContentId(f"content-deb-releases-{uuid4()}")


def gen_release_component_id() -> ContentId:
    return ContentId(f"content-deb-release_components-{uuid4()}")


def gen_package_release_component_id() -> ContentId:
    return ContentId(f"content-deb-package_release_components-{uuid4()}")
