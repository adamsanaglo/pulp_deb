import typer

from pmc.client import get_client, handle_response

app = typer.Typer()
repo = typer.Typer()
package = typer.Typer()
app.add_typer(repo, name="repo", help="Manage repo access")
app.add_typer(package, name="package", help="Manage package")

ACCOUNT_NAMES_HELP = "Semicolon-separated list of account names you want to operate on."
REPO_REGEX_HELP = "A regular expression that matches the names of the repos."
REPO_OPERATOR_HELP = "Whether or not to grant the Repo Operator special role."
PACKAGE_NAMES_HELP = "Semicolon-separated list of package names you want to operate on."


@repo.command(name="list")
def repo_access_list(ctx: typer.Context) -> None:
    """List all repo access records"""
    with get_client(ctx.obj) as client:
        resp = client.get("/access/repo/")
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
        "account_names": account_names.split(";"),
        "repo_regex": repo_regex,
    }
    if operator:
        data["operator"] = str(operator)
    with get_client(ctx.obj) as client:
        resp = client.post("/access/repo/grant/", json=data)
        handle_response(ctx.obj, resp)


@repo.command(name="revoke")
def repo_access_revoke(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
) -> None:
    """Revoke account(s) access to repo(s)"""
    data = {"account_names": account_names.split(";"), "repo_regex": repo_regex}
    with get_client(ctx.obj) as client:
        resp = client.post("/access/repo/revoke/", json=data)
        handle_response(ctx.obj, resp)


@package.command(name="list")
def package_ownership_list(ctx: typer.Context) -> None:
    """List all package ownership records"""
    with get_client(ctx.obj) as client:
        resp = client.get("/access/package/")
        handle_response(ctx.obj, resp)


@package.command(name="grant")
def package_ownership_grant(
    ctx: typer.Context,
    account_names: str = typer.Argument(..., help=ACCOUNT_NAMES_HELP),
    repo_regex: str = typer.Argument(..., help=REPO_REGEX_HELP),
    package_names: str = typer.Argument(..., help=PACKAGE_NAMES_HELP),
) -> None:
    data = {
        "account_names": account_names.split(";"),
        "repo_regex": repo_regex,
        "package_names": package_names.split(";"),
    }
    """Grant account(s) ownership of package(s) in specific repo(s)"""
    with get_client(ctx.obj) as client:
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
        "account_names": account_names.split(";"),
        "repo_regex": repo_regex,
        "package_names": package_names.split(";"),
    }
    with get_client(ctx.obj) as client:
        resp = client.post("/access/package/revoke/", json=data)
        handle_response(ctx.obj, resp)
