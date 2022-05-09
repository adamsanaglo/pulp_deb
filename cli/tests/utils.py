from typing import Dict
from uuid import uuid4

from pmc.schemas import DistroType, RepoType


def gen_repo_attrs() -> Dict[str, str]:
    return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=RepoType.apt)


def gen_distro_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_distro_{uuid4()}",
        type=DistroType.apt,
        base_path=f"{uuid4()}/{uuid4()}",
    )


def gen_publisher_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_publisher_{uuid4()}",
        contact_email="alice@contoso.com;bob@contoso.com",
        icm_service="test_icm_service",
        icm_team="test_icm_team",
    )
