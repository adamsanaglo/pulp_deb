# pmc CLI installation and usage

Publishers operate on PMC repos via the `pmc` client CLI.
- [Installing the PMC Client](#installing-the-pmc-client)
- [Configuration File](#configuration-file)
    - [Sample Config](#sample-config)
- [Usage](#usage)
    - [List Resources](#list-resources)
    - [Add/Remove Packages](#addremove-packages)

## Installing the pmc client

### Azure Artifacts

The recommended way to install the pmc client in Azure DevOps is to set up your own Azure Artifacts feed
which will pull in the pmc-cli package from our [Compute-PMC Azure Artifacts
feed](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC@Release/PyPI/pmc-cli/overview/).

First set up an Azure Artifacts feed feed in your org or project and then [configure the Compute-PMC
feed as an upstream Python
source](https://eng.ms/docs/cloud-ai-platform/devdiv/one-engineering-system-1es/1es-docs/azure-artifacts/troubleshooting/how-to-add-upstream-sources-to-azure-artifacts-feed).

If you're in the msazure org, select "Azure Artifacts feed in this organization", select
"Compute-PMC" as the feed and then "Release" as the view.

If you're outside the msazure org, select "Azure Artifacts in another orgazation" and enter
"azure-feed://msazure/Compute-PMC@Release" as your feed.

After your Azure Artifacts feed has been set up, when you search for Python packages from upstream
sources, you should see the pmc-cli package.

After you have set up your Azure Artifact feed, you can use [the PipAuthenticate task to
authenticate and then download the pmc-cli
client](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/pip-authenticate-v1).

### Installing directly

If you aren't using ADO, then you can install the pmc-cli directly.

One option is to follow the [Azure Artifact instructions for setting up pip to use the Compute-PMC
feed](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/connect/pip) and then run
`pip install pmc-cli`.

Alternatively, you can simply install the pmc-cli with a single command but you will need [a
personal access token](https://msazure.visualstudio.com/_usersSettings/tokens):

```bash
pip install --index-url https://msazure.pkgs.visualstudio.com/_packaging/Compute-PMC/pypi/simple/ "pmc-cli>0.0"
```

## Configuration file

While the `pmc` command has command-line options which let you specify all information needed to interact with the publishing system, it's much easier to use a configuration file which lets you provide overrideable defaults.

The `pmc` command uses `~/.config/pmc/settings.toml` as the default location of the configuration file. You can be override that with the `--config` option.

See the sample config (below) for more information.

### Sample config

The sample config below has profiles for both tux-dev and prod. You may choose to only set up only
one profile in your settings.toml file though if you are using only one environment.

If you have multiple profiles, use the `--profile` option to select the one you want to use
(e.g. `pmc --profile prod repo list`).

For each profile you'll need to populate two fields:
- Set `msal_client_id` to be the Client ID associated with the security principal you setup for publishing activities.
- Set `msal_cert_path` to be the path to the file containing the cert (with public and private key) associated with the security principal.

```toml
[tuxdev]
base_url = "https://tux-ingest.corp.microsoft.com/api/v4"
msal_client_id = "YOUR_TUX_CLIENT_ID"
msal_scope = "api://55391a9d-3c3b-4e4a-afa6-0e49c2245175/.default"
msal_cert_path = "/PATH/TO/YOUR/TUX_CERT"
msal_SNIAuth = true
msal_authority = "https://login.microsoftonline.com/Microsoft.onmicrosoft.com"

[prod]
base_url = "https://pmc-ingest.trafficmanager.net/api/v4"
msal_client_id = "YOUR_PROD_CLIENT_ID"
msal_scope = "api://d48bb382-20ec-41b9-a0ea-07758a21ccd0/.default"
msal_cert_path = "/PATH/TO/YOUR/PROD_CERT"
msal_SNIAuth = true
msal_authority = "https://login.microsoftonline.com/MSAzureCloud.onmicrosoft.com"
```

## Usage

The `pmc` command looks somewhat like the old `pmctool` but is richer and better organized.
The `pmc --help` command will provide a brief but complete summary of the commands available through the CLI.

Some sample commands are shown below.

### List Resources

```bash
# List Repositories:
pmc repo list

# List all .deb Packages
pmc package deb list

# List all .rpm Packages
pmc package rpm list

# List the .rpm Packages in a Repo:
pmc package rpm list --repo $REPO_NAME

# Responses are paginated, so you'll only receive the first 100 responses by default
# Use --offset to see the next "page" of resources
pmc repo list --offset 100

# Use --limit to change the number of returned resources
pmc repo list --limit 50
```

### Add/Remove Packages

```bash
# Upload a package
pmc package upload [FILE]

# Add one or more packages to a repo
pmc repo package update --add-packages $PKG_ID,... $REPO_MAME [$RELEASE]

# Remove one or more packages from a repo
pmc repo package update --remove-packages $PKG_ID,... $REPO_NAME [$RELEASE]
```
