from typing import Dict
from uuid import uuid4

from pmc.schemas import DistroType, RepoType


def gen_repo_attrs() -> Dict[str, str]:
    return dict(name=f"pmc_cli_test_repo_{uuid4()}", type=RepoType.apt)


def gen_distro_attrs() -> Dict[str, str]:
    return dict(
        name=f"pmc_cli_test_distro_{uuid4()}",
        type=DistroType.apt,
        path=f"{uuid4()}/{uuid4()}",
    )
