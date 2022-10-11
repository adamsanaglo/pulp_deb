import json
from pathlib import Path
from typing import Any, Optional

import pytest

from pmc.schemas import Role
from tests.conftest import package_upload_command
from tests.utils import become, invoke_command

# Note that "package upload" is exercised by fixture.


def test_upload_file_type(orphan_cleanup: None) -> None:
    become(Role.Package_Admin)

    # file without file type
    path = Path.cwd() / "tests" / "assets" / "hello.txt"
    result = invoke_command(["package", "upload", str(path)])
    assert result.exit_code != 0
    assert "Unrecognized file extension" in result.stdout

    # python with file type
    path = Path.cwd() / "tests" / "assets" / "helloworld-0.0.1.tar.gz"
    result = invoke_command(["package", "upload", "--type", "python", str(path)])
    assert result.exit_code == 0


def _assert_package_list_not_empty(type: str, file_type: Optional[str] = None) -> None:
    result = invoke_command(["package", type, "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_deb_list(deb_package: Any) -> None:
    _assert_package_list_not_empty("deb")


def test_rpm_list(rpm_package: Any) -> None:
    _assert_package_list_not_empty("rpm")


def test_file_list(file_package: Any) -> None:
    _assert_package_list_not_empty("file", "file")


def test_python_list(python_package: Any) -> None:
    _assert_package_list_not_empty("python")


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
