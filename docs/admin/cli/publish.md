# Publishing

This document describes how to package and publish the CLI.

## PyPI

While we publish the pmc-cli package to packages.microsoft.com, there is an empty package on PyPI at
`https://pypi.org/project/pmc-cli/`. The purpose of this package is to reserve the pmc-cli name and
to prevent a nefarious actor from publishing their own pmc-cli package which our publishers might
accidentally install and use.

## Server Setup

These steps describe how to prepare the PMC server to distribute the CLI package. They assume that
your pmc client is setup using the repo admin credentials and that you want to distribute the
package at `pmc-cli`. They only need to be performed once per environment.

```
# create a repo named pmc-cli-python
pmc repo create pmc-cli-python python

# create a pypi distro called 'pmc-cli' that serves from a folder 'pmc-cli'
pmc distro create pmc-cli pypi pmc-cli --repository pmc-cli-python
```

## Publishing setup

### Azure Artifacts

In order to upload and publish to the Compute-PMC feed, you'll need to be a feed Contributor, Owner,
or Administrator. By default the PMC team in ADO has Owner access to the Azure Artifact feed. If you
are not on the PMC team or wish to customize your role/permissions, visit [the feed permissions
setting page](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/settings/permissions).

When you upload to the feed, you'll need to use your username and a password. The password
is a Personal Access token that can be acquired at
<https://msazure.visualstudio.com/_usersSettings/tokens>. The token will need the permission to
read/write/manage packages.

### packages.microsoft.com

First, download the prod-publisher.pem cert from the production keyvault and then set up the following
profile in your settings.toml:

```
[prod-publisher]
base_url = "https://pmc-ingest.trafficmanager.net/api/v4"
msal_client_id = "bfdb84f5-ca97-4f33-8b09-ea99412763de"
msal_scope = "api://d48bb382-20ec-41b9-a0ea-07758a21ccd0/.default"
msal_cert_path = "~/.config/pmc/prod-publisher.pem"
msal_authority = "https://login.microsoftonline.com/MSAzureCloud.onmicrosoft.com"
```

Then you can either set `--profile prod-publisher` with each cli command or you can run:

```
export PMC_CLI_PROFILE="prod-publisher"
```

## Packaging and Uploading

After you've set up your CLI:

1. First, identify the version you want to publish and export it (`export VERSION="x.x.x"`)
1. Open up pyproject.toml file and update the version field if necessary.
1. Next, update the change log with `towncrier build --yes --version $VERSION`.
1. Open a PR with your changes and get it merged.
1. Once the PR is merged, create a new cli-x.x.x tag at <https://msazure.visualstudio.com/One/_git/Compute-PMC/tags>
1. Next run the following commands from your cli directory

```
git fetch -t
git checkout cli-$VERSION

poetry build

# Azure Artifacts
export POETRY_REPOSITORIES_AZURE_URL="https://msazure.pkgs.visualstudio.com/_packaging/Compute-PMC/pypi/upload/"
poetry publish -r azure -u <username> -p <password>

# packages.microsoft.com
PACKAGE_ID=$(pmc --id-only package upload dist/pmc_cli-${VERSION}-py3-none-any.whl)
pmc repo packages update pmc-cli-python --add-packages $PACKAGE_ID
pmc repo publish pmc-cli-python
```

Visit
<https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/versions/>, find the
latest version and click the "Promote" button to promote the package to a "Release". If you aren't
able to promote the package version, see the setup section of this doc for info about permissions.

Lastly check <https://packages.microsoft.com/pmc-cli/> to ensure the package is there as well.
