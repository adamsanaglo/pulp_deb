import json
from typing import Any

from tests.utils import invoke_command


# Note that "package upload" is exercised by fixture.


def test_list(package: Any) -> None:
    result = invoke_command(["package", "list"])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert len(response) > 0


def test_show(package: Any) -> None:
    result = invoke_command(["package", "show", package["id"]])
    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert package["id"] == response["id"]