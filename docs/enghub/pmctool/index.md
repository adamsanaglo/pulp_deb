# pmc CLI Documentation

Publishers operate on PMC repos via the `pmc` client CLI.

## Installing the pmc client

The pmc client is a python package. This package is not published externally; it can only be installed from within corpnet.

```
pip install –extra-index-url http://tux-devrepo.corp.microsoft.com/pypi/pmc/simple/ pmc-cli
```

You can also download the latest .whl file from that endpoint and add that file to any environment which cannot access the corp.microsoft.com domain. The `pip` command can be used to install the pmc command from the .whl file; pip will resolve dependencies from the usual Python package source on the internet.

## Configuration file

While the `pmc` command has command-line options which let you specify all information needed to interact with the publishing system, it's much easier to use a configuration file which lets you provide overrideable defaults.

The `pmc` command uses `~/.config/pmc/settings.toml` as the default location of the configuration file. You can be override that with the `--config` option.

The command `pmc config create --edit` will create a default configuration file (in the default location) and bring it up in your editor for you to customize.
You will need to update some information within that file; see the sample (below) for more information.

### Sample config file for tuxdev

In this sample configuration file, you must update these values:

- Set `msal_client_id` to be the Client ID associated with the security principal you setup for publishing activities.
- Set `msal_cert_path` to be the absolute path to the file containing the cert (with public and private key) associated with the security principal.

```
[cli]
no_wait = false
no_color = false
id_only = false
format = "json"
debug = false
base_url = "https://tux-ingest.corp.microsoft.com/api/v4"
msal_client_id = "YOUR_CLIENT_ID"
msal_scope = "api://55391a9d-3c3b-4e4a-afa6-0e49c2245175/.default"
msal_cert_path = "/PATH/TO/YOUR/CERT"
msal_SNIAuth = true
msal_authority = "https://login.microsoftonline.com/Microsoft.onmicrosoft.com"
```

### Sample config file for Prod

In this sample configuration file, you must update these values:

- Set `msal_client_id` to be the Client ID associated with the security principal you setup for publishing activities.
- Set `msal_cert_path` to be the absolute path to the file containing the cert (with public and private key) associated with the security principal.

```
[cli]
no_wait = false
no_color = false
id_only = false
format = "json"
debug = false
base_url = "https://pmc-ingest.trafficmanager.net/api/v4"
msal_client_id = "YOUR_CLIENT_ID"
msal_scope = "api://d48bb382-20ec-41b9-a0ea-07758a21ccd0/.default"
msal_cert_path = "/PATH/TO/YOUR/CERT"
msal_SNIAuth = true
msal_authority = "https://login.microsoftonline.com/MSAzureCloud.onmicrosoft.com"
```

## Usage

The `pmc` command looks somewhat like the old `pmctool` but is richer and better organized.
The `pmc --help` command will provide a brief but complete summary of the commands available through the CLI.

Some sample commands are shown below.

### List Resources
```
# List Repositories:
pmc repo list

# List all .deb Packages
pmc package deb list

# List all .rpm Packages
pmc package rpm list

# List the Packages in a Repo:
pmc repo package list $REPO_NAME

# Responses are paginated, so you'll only receive the first 100 responses by default
# Use --offset to see the next "page" of resources
pmc repo list --offset 100

# Use --limit to change the number of returned resources
pmc repo list --limit 50
```

### Add/Remove Packages
```
# Upload a package
pmc package upload [FILE]

# Add one or more packages to a repo
pmc repo package update --add-packages $PKG_ID;... $REPO_MAME [$RELEASE]

# Remove one or more packages from a repo
pmc repo package update --remove-packages $PKG_ID;... $REPO_NAME [$RELEASE]
```