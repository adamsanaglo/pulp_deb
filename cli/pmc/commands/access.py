from typing import Optional

import typer

from pmc.client import client, handle_response
from pmc.constants import LIST_SEPARATOR
from pmc.utils import UserFriendlyTyper, id_or_name

app = UserFriendlyTyper()
repo = UserFriendlyTyper()
package = UserFriendlyTyper()
app.add_typer(repo, name="repo", help="Manage repo access")
app.add_typer(package, name="package", help="Manage package")

ACCOUNT_NAMES_HELP = (
    f"{LIST_SEPARATOR.title}-separated list of account names you want to operate on."
)
REPO_REGEX_HELP = "A regular expression that matches the names of the repos."
REPO_OPERATOR_HELP = "Whether or not to grant the Repo Operator special role."
PACKAGE_NAMES_HELP = (
    f"{LIST_SEPARATOR.title}-separated list of package names you want to operate on."
)
REPO_CLONE_HELP = "Repository id or name to clone permissions %s"


account_filter_option = id_or_name(
    "accounts", typer.Option(None, help="Filter by account id or name.")
)


@repo.command(name="list")
def repo_access_list(
    ctx: typer.Context,
    account: Optional[str] = account_filter_option,
) -> None:
    """List all repo access records"""
    params = {}
    if account:
        params["account"] = account
    resp = client.get("/access/repo/", params=params)
    handle_response(ctx.obj, resp)


@repo.command(name="grant")
def repo_access_grant(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
    operator: bool = typer.Option(None, help=REPO_OPERATOR_HELP),
) -> None:
    """Grant account(s) access to repo(s)"""
    data = {
        "account_names": account_names.split(LIST_SEPARATOR),
        "repo_regex": repo_regex,
    }
    if operator:
        data["operator"] = str(operator)
    resp = client.post("/access/repo/grant/", json=data)
    handle_response(ctx.obj, resp)


@repo.command(name="revoke")
def repo_access_revoke(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
) -> None:
    """Revoke account(s) access to repo(s)"""
    data = {"account_names": account_names.split(LIST_SEPARATOR), "repo_regex": repo_regex}
    resp = client.post("/access/repo/revoke/", json=data)
    handle_response(ctx.obj, resp)


@repo.command(name="clone")
def repo_access_clone(
    ctx: typer.Context,
    new_repo: str = id_or_name("repositories", typer.Argument(..., help=REPO_CLONE_HELP % "into")),
    old_repo: str = id_or_name("repositories", typer.Argument(..., help=REPO_CLONE_HELP % "from")),
) -> None:
    """Additively clone repo access from one repo to another."""
    resp = client.post(f"/access/repo/{new_repo}/clone_from/{old_repo}/")
    handle_response(ctx.obj, resp)


@package.command(name="list")
def package_ownership_list(
    ctx: typer.Context,
    account: Optional[str] = account_filter_option,
) -> None:
    """List all package ownership records"""
    params = {}
    if account:
        params["account"] = account
    resp = client.get("/access/package/", params=params)
    handle_response(ctx.obj, resp)


@package.command(name="grant")
def package_ownership_grant(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
    package_names: str = typer.Argument(..., help=PACKAGE_NAMES_HELP),
) -> None:
    data = {
        "account_names": account_names.split(LIST_SEPARATOR),
        "repo_regex": repo_regex,
        "package_names": package_names.split(LIST_SEPARATOR),
    }
    """Grant account(s) ownership of package(s) in specific repo(s)"""
    resp = client.post("/access/package/grant/", json=data)
    handle_response(ctx.obj, resp)


@package.command(name="revoke")
def package_ownership_revoke(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
    package_names: str = typer.Argument(..., help=PACKAGE_NAMES_HELP),
) -> None:
    """Revoke account(s) ownership of package(s) in specific repo(s)"""
    data = {
        "account_names": account_names.split(LIST_SEPARATOR),
        "repo_regex": repo_regex,
        "package_names": package_names.split(LIST_SEPARATOR),
    }
    resp = client.post("/access/package/revoke/", json=data)
    handle_response(ctx.obj, resp)
