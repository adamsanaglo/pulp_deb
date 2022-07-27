import json
from typing import Any

import pytest

from pmc.schemas import Role
from tests.conftest import package_upload_command
from tests.utils import become, invoke_command

# Note that "package upload" is exercised by fixture.


def _assert_package_list_not_empty(type: str) -> None:
    result = invoke_command(["package", type, "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_deb_list(deb_package: Any) -> None:
    _assert_package_list_not_empty("deb")


def test_rpm_list(rpm_package: Any) -> None:
    _assert_package_list_not_empty("rpm")


def test_show(deb_package: Any) -> None:
    result = invoke_command(["package", "show", deb_package["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert deb_package["id"] == response["id"]


def test_zst_deb(zst_deb_package: Any) -> None:
    """This empty test ensures we handle zst packages correctly by exercising the fixture."""
    pass


@pytest.mark.parametrize("package", ["unsigned.deb", "unsigned.rpm", "signed-by-other.rpm"])
def test_unsigned_package(package: str) -> None:
    become(Role.Package_Admin)
    cmd = package_upload_command(package)
    result = invoke_command(cmd)
    assert result.exit_code != 0
    assert "UnsignedPackage" in result.stdout


def test_ignore_signature(forced_unsigned_package: Any) -> None:
    """This empty test ensures forcing an unsigned package works by exercising the fixture."""
    pass
