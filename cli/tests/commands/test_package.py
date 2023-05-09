import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional

import pytest

from pmc.schemas import Role
from tests.conftest import package_upload_command
from tests.utils import invoke_command

# Note that "package upload" is exercised by fixture.


PACKAGE_URL = "https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb"
FILE_URL = "https://packages.microsoft.com/keys/microsoft.asc"


def test_upload_file_type(orphan_cleanup: None) -> None:
    # file without file type
    path = Path.cwd() / "tests" / "assets" / "hello.txt"
    result = invoke_command(["package", "upload", str(path)], role=Role.Package_Admin)
    assert result.exit_code != 0
    assert "Could not determine package type" in result.stdout

    # python with file type
    path = Path.cwd() / "tests" / "assets" / "helloworld-0.0.1.tar.gz"
    result = invoke_command(
        ["package", "upload", "--type", "python", str(path)], role=Role.Package_Admin
    )
    assert result.exit_code == 0


def _list_packages(type: str, filters: Optional[Dict[str, Any]] = None) -> Any:
    cmd = ["package", type, "list"]

    if filters:
        for key, val in filters.items():
            cmd.extend([f"--{key}", val])

    result = invoke_command(cmd)
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    return response


def _assert_package_list_not_empty(type: str, filters: Optional[Dict[str, Any]] = None) -> None:
    response = _list_packages(type, filters)
    assert response["count"] > 0


def _assert_package_list_empty(type: str, filters: Optional[Dict[str, Any]] = None) -> None:
    response = _list_packages(type, filters)
    assert response["count"] == 0


def test_deb_list(deb_package: Any) -> None:
    _assert_package_list_not_empty("deb")
    _assert_package_list_not_empty("deb", {"name": deb_package["name"]})
    _assert_package_list_empty("deb", {"name": "notarealpackagename"})
    _assert_package_list_not_empty("deb", {"version": deb_package["version"]})
    _assert_package_list_empty("deb", {"arch": "flux64"})
    # Tests hashing and sha-filter. This file is uploaded by the deb_package fixture.
    _assert_package_list_not_empty("deb", {"file": "tests/assets/signed-by-us.deb"})


def test_deb_src_list(deb_src_package: Any) -> None:
    _assert_package_list_not_empty("debsrc")
    _assert_package_list_not_empty("debsrc", {"name": deb_src_package["name"]})
    _assert_package_list_empty("debsrc", {"name": "notarealpackagename"})
    _assert_package_list_not_empty("debsrc", {"version": deb_src_package["version"]})
    _assert_package_list_empty("debsrc", {"arch": "flux64"})
    _assert_package_list_not_empty("debsrc", {"relative-path": deb_src_package["relative_path"]})
    _assert_package_list_empty("debsrc", {"relative-path": "nonexistingrelativepath"})
    assert len(deb_src_package["artifacts"]) == len(set(deb_src_package["artifacts"].values())) == 3


def test_rpm_list(rpm_package: Any) -> None:
    _assert_package_list_not_empty("rpm")
    _assert_package_list_not_empty("rpm", {"name": rpm_package["name"]})
    _assert_package_list_empty("rpm", {"name": "notarealpackagename"})
    _assert_package_list_not_empty("rpm", {"version": rpm_package["version"]})
    _assert_package_list_empty("rpm", {"version": "0.0.0.0.0.0.0.0.1"})
    _assert_package_list_not_empty("rpm", {"release": rpm_package["release"]})
    _assert_package_list_empty("rpm", {"release": "9el1"})
    # Tests hashing and sha-filter. This file is uploaded by the rpm_package fixture.
    _assert_package_list_not_empty("rpm", {"file": "tests/assets/signed-by-us.rpm"})


def test_rpm_list_with_ordering(rpm_package: Any, forced_unsigned_package: Any) -> None:
    response = _list_packages("rpm", {"ordering": "name"})
    assert len(response["results"]) > 1
    print(response["results"])
    assert response["results"][1]["name"] > response["results"][0]["name"]

    response = _list_packages("rpm", {"ordering": "-name"})
    assert len(response["results"]) > 1
    print(response["results"])
    assert response["results"][1]["name"] < response["results"][0]["name"]


def test_file_list(file_package: Any) -> None:
    _assert_package_list_not_empty("file")
    _assert_package_list_not_empty("file", {"relative-path": file_package["relative_path"]})
    _assert_package_list_empty("file", {"relative-path": "does/not/exist.exe"})


def test_python_list(python_package: Any) -> None:
    _assert_package_list_not_empty("python")
    _assert_package_list_not_empty("python", {"name": python_package["name"]})
    _assert_package_list_empty("python", {"name": "sneks"})
    _assert_package_list_not_empty("python", {"filename": python_package["filename"]})
    _assert_package_list_empty("python", {"filename": "sneks-0.0.1-py3-none-any.whl"})


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
    cmd = package_upload_command(package)
    result = invoke_command(cmd, role=Role.Package_Admin)
    assert result.exit_code != 0
    assert "PackageSignatureError" in result.stdout


def test_mariner_package(orphan_cleanup: None) -> None:
    cmd = package_upload_command("signed-by-mariner.rpm")
    result = invoke_command(cmd, role=Role.Package_Admin)
    assert result.exit_code == 0
    assert "PackageSignatureError" not in result.stdout


def test_invalid_rpm_package_upload() -> None:
    """Test uploading a text file as an rpm package."""
    path = str(Path.cwd() / "tests" / "assets" / "invalid.rpm")

    # package signature verification fails
    result = invoke_command(["package", "upload", path], role=Role.Package_Admin)
    assert result.exit_code != 0
    assert "PackageSignatureError" in result.stdout

    # pulp fails to parse the package
    result = invoke_command(
        ["package", "upload", "--ignore-signature", path], role=Role.Package_Admin
    )
    assert result.exit_code != 0
    assert "RPM file cannot be parsed for metadata" in result.stdout


def test_invalid_deb_package_upload() -> None:
    """Test uploading a text file as a deb package."""
    path = str(Path.cwd() / "tests" / "assets" / "invalid.deb")

    # package signature verification fails
    result = invoke_command(["package", "upload", path], role=Role.Package_Admin)
    assert result.exit_code != 0
    assert "PackageSignatureError" in result.stdout

    # pulp fails to parse the package
    result = invoke_command(
        ["package", "upload", "--ignore-signature", path], role=Role.Package_Admin
    )
    assert result.exit_code != 0
    assert "Unable to find global header" in result.stdout


def test_deb_src_package_upload_no_artifacts() -> None:
    result = invoke_command(
        package_upload_command("hello_2.10-2ubuntu2.dsc"), role=Role.Package_Admin
    )
    assert result.exit_code != 0
    assert "A source file is listed in the DSC file but is not yet available" in result.stdout


def test_ignore_signature(forced_unsigned_package: Any) -> None:
    """This empty test ensures forcing an unsigned package works by exercising the fixture."""
    pass


def test_package_upload_by_url(orphan_cleanup: None) -> None:
    """Test a package upload by using a url."""
    result = invoke_command(["package", "upload", PACKAGE_URL], role=Role.Package_Admin)
    assert result.exit_code == 0

    result = invoke_command(["package", "upload", FILE_URL], role=Role.Package_Admin)
    assert result.exit_code == 1
    assert "Could not determine package type" in result.stdout

    result = invoke_command(
        ["package", "upload", "--type", "file", FILE_URL], role=Role.Package_Admin
    )
    assert result.exit_code == 0


def test_package_directory_upload(orphan_cleanup: None) -> None:
    package_names = ["hello.txt", "test.txt"]
    with TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir)

        for file in package_names:
            with (package_dir / file).open("w") as f:
                f.write(file)

        result = invoke_command(
            ["package", "upload", "--type", "file", str(package_dir)], role=Role.Package_Admin
        )

    packages = json.loads(result.stdout)
    assert sorted([pkg["relative_path"] for pkg in packages]) == sorted(package_names)

    assert result.exit_code == 0


def test_duplicate_deb_package(deb_package: Any) -> None:
    result = invoke_command(package_upload_command("signed-by-us.deb"), role=Role.Package_Admin)
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["id"] == deb_package["id"]


def test_duplicate_deb_src_package(deb_src_package: Any) -> None:
    result = invoke_command(
        package_upload_command("hello_2.10-2ubuntu2.dsc"), role=Role.Package_Admin
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["id"] == deb_src_package["id"]


def test_duplicate_rpm_package(deb_package: Any) -> None:
    result = invoke_command(package_upload_command("signed-by-us.deb"), role=Role.Package_Admin)
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["id"] == deb_package["id"]


def test_duplicate_file_package(deb_package: Any) -> None:
    result = invoke_command(package_upload_command("signed-by-us.deb"), role=Role.Package_Admin)
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["id"] == deb_package["id"]
