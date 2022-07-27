## Config

Users can configure their cli clients with a config file. To create a new config file, see `pmc
config create --help`. Users can also edit an existing config file with `pmc config edit`.

Supported formats are json and toml, and must be stored in either a file ending in `.json` or
`.toml` respectively.

By default, pmc cli will look for a config file in the user's config path. The path depends on the
OS but `pmc --help` will show the default locations.

The config file location may also be specified by setting an environment variable (`PMC_CLI_CONFIG`)
or setting `--config` when running pmc (ie `pmc --config ~/settings.toml ...`).

## Authentication Options
Repo API calls require Azure Active Directory (AAD) Authentication, which is handled by the Microsoft Authentication Library (MSAL).
Authentication is a 3 step process.
1. Request a token from AAD (specifically the `MSAL authority`) for a specified `scope` (the API server)
2. Receive a token from AAD
3. Send the token to the API

The options below enable authentication, which can be specified in the Config or the command line.

Config        | CLI            | Description
--------------|----------------|-------------------
msal_client_id|--msal-client-id| Application ID for the Service Principal that will be used for authentication
msal_cert_path|--msal-cert-path| Path to a cert that will authenticate the Service Principal
msal_SNIAuth  |--msal-sniauth  | Use Subject Name Issuer Authentication (to enable certificate autorotation)
msal_authority|--msal-authority| The AAD authority from which a token will be requested (i.e. https://login.microsoftonline.com/...)
msal_scope    |--msal-scope    | The scope for which a token will be requested (i.e. api://1ce02e3e...)


## Dev Environment

First, install poetry via pipx:

```
pip install pipx
pipx install poetry
```

By default poetry creates the virtual environment inside your home folder which can sometimes be
problematic for tools such as IDEs which may need to be aware of your dependencies so you may choose
to configure poetry to create your virtual environment inside your project folder:

```
poetry config virtualenvs.in-project true
```

And then install the cli dependencies:

```
poetry install
```

To run commands, either load your poetry environment:

```
poetry shell
pmc repo list
```

Or use `poetry run`:

```
poetry run pmc repo list
```

## Configuring Authentication
A default Service Principal is available to simplify your dev environment
1. Run `make config`
  - This will generate a config in the default location (~/.config/pmc/settings.toml)
  - It will prepopulate this config file with the necessary settings.
2. Download the latest PEM file from [Azure Keyvault](https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/asset/Microsoft_Azure_KeyVault/Certificate/https://mb-repotest.vault.azure.net/certificates/esrp-auth-test) and place it in `~/.config/pmc/auth.pem`
3. Create an account with the role you want to test.
  - `./update_role.sh Repo_Admin --create`
  - You can call this script again any time you wish to change roles (`./update_role.sh Account_Admin`)

## Example Workflow

```
# create a repo
REPO_ID=$(pmc --id-only repo create myrepo apt)

# create a distro
pmc distro create mydistro apt "some/path" --repository $REPO_ID

# upload a package
cp tests/assets/signed-by-us.deb .
PACKAGE_ID=$(pmc --id-only package upload signed-by-us.deb)

# add our package to the repo
pmc repo packages update $REPO_ID --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish $REPO_ID

# check out our repo
http :8080/pulp/content/some/path/
```
