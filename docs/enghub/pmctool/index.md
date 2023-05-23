# pmc CLI installation and usage

Publishers operate on PMC repos via the `pmc` client CLI.
- [Installing the PMC Client](#installing-the-pmc-client)
- [Configuration File](#configuration-file)
    - [Sample Config](#sample-config)
- [Usage](#usage)
    - [List Resources](#list-resources)
    - [Publishing Packages](#publishing-packages)

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

If you're outside the msazure org, select "Azure Artifacts in another organization" and enter
"azure-feed://msazure/Compute-PMC@Release" as your feed.

To check to see if the upstream is set up correct, go to your Azure Artifacts feed page.
Hit the "Search Upstream Sources" button, select "Python", and enter "pmc-cli" in the search box.
If configured properly, you should see various versions of the pmc-cli package.

To use the Azure Artifacts feed in a pipeline, you must give the build service permissions to your
Azure Artifact feed. See the [Azure Artifacts docs on how to do
this](https://learn.microsoft.com/en-us/azure/devops/artifacts/feeds/feed-permissions?view=azure-devops#pipelines-permissions).

After you have set up your Azure Artifact feed, you can use [the PipAuthenticate task to
authenticate and then download the pmc-cli
client](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/pip-authenticate-v1):

```yaml
- task: PipAuthenticate@1
  inputs:
    artifactFeeds: 'myproject/myfeed'
- script: pip install pmc-cli
```

If you run into installation problems, you can use "pip install -vvv pmc-cli" to help debug.

You may get an error message such as "User '464e3c60-f66b-11ed-b67e-0242ac120002' lacks permission to complete this action.",
You can use the ADO api to look up the user (e.g. `https://vssps.dev.azure.com/{YOUR ORG HERE}/_apis/identities/464e3c60-f66b-11ed-b67e-0242ac120002`).
This will give you the user name which you can then add to your feed as a Contributor.

Also, you can [reach out to the Azure Artifacts team for
help](https://eng.ms/docs/cloud-ai-platform/devdiv/one-engineering-system-1es/1es-docs/azure-artifacts/office-hours).

### Installing directly

If you aren't using ADO, then you can install the pmc-cli directly.

One option is to follow the [Azure Artifact instructions for setting up pip to use the Compute-PMC
feed](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/connect/pip) and then run
`pip install pmc-cli`.

Alternatively, you can simply install the pmc-cli with a single command but you will need [a
personal access token](https://msazure.visualstudio.com/_usersSettings/tokens):

```bash
pip install --index-url https://msazure.pkgs.visualstudio.com/_packaging/Compute-PMC%40Release/pypi/simple/ pmc-cli
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

### Publishing packages

For information on how to publish packages with the CLI, see [the Publishing
page](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/publish#publishing-the-package).
