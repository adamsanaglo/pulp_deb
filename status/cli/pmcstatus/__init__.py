import json
import requests
from requests.exceptions import HTTPError, ConnectionError
import click


@click.group()
def main():
    """CLI with helpful tools for managing the PMC status site."""
    pass


@main.command(help=(
    "Publish a repository status update to the PMC Status website. "
    "If required parameters are not provided, then they can be entered through prompts.")
)
@click.option(
    "-t", "--repo-type", "repo_type", required=True,
    type=click.Choice(['apt', 'yum'], case_sensitive=False),
    prompt="Type of repository",
    help="Either 'apt' or 'yum."
)
@click.option(
    "-r", "--repo-url", "repo_url", required=True,
    type=str,
    prompt="URL of repository",
    help="URL of the apt or yum repository."
)
@click.option(
    "-d", "--dists", "dists",
    type=str,
    default=None,
    help="Comma separated list of apt distributions."
)
@click.option(
    "-n", "--function-app-name", "function_app_name", required=True,
    type=str,
    prompt="Function app name",
    help="Name of the Azure Function App that checks repositories "
         "(contains functions 'generate_repo' & 'check_repo')."
)
@click.option(
    "-k", "--master-key", "master_key",
    type=str,
    hide_input=True,
    prompt="Function app master key",
    help="Function app master key. Please provide this when prompted."
)
def publish(
    repo_type: str,
    repo_url: str,
    dists: str,
    function_app_name: str,
    master_key: str
):
    """Publish repository status to the PMC status website."""
    request_location = f"https://{function_app_name}.azurewebsites.net/admin/functions/check_repo"
    headers = {"Content-Type": "application/json", "x-functions-key": master_key}

    request = {
        "type": repo_type,
        "repo": repo_url
    }

    if dists:
        request["dists"] = dists.split(",")

    body = {"input": json.dumps(request)}

    try:
        response = requests.post(
            request_location,
            headers=headers,
            json=body
        )
        response.raise_for_status()
    except HTTPError as e:
        if e.response.status_code == 401:
            print("Make sure that the function app master key is correct.")
        print(f"Failure: {e}")
    except ConnectionError as e:
        print("Make sure that the function app name is correct.")
        print(f"Failure: {e}")
    else:
        print("Success")


if __name__ == "__main__":
    main()
