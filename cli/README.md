## Config

Users can configure their cli clients with a config file. To create a new config file, see `pmc
config create --help`. Users can also edit an existing config file with `pmc config edit`.

Supported formats are json and toml, and must be stored in either a file ending in `.json` or
`.toml` respectively.

By default, pmc cli will look for a config file in the user's config path. The path depends on the
OS but `pmc --help` will show the default locations.

The config file location may also be specified by setting an environment variable (`PMC_CLI_CONFIG`)
or setting `--config` when running pmc (ie `pmc --config ~/settings.toml ...`).

## Show Restricted Commands
Many commands are restricted and Publishers are not allowed to run them.
As a result they are hidden by default in the cli.
To show all commands you must set a variable in your settings config:
```
hide_restricted_commands = false
```

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

## Workflows

Once you've set up the server and CLI, view the `docs/admin/workflows.md` file for some example
workflows.

## Publishing

### Server Setup

These steps describe how to prepare the PMC server to distribute the CLI package. They assume that
your pmc client is setup for the server and that you want to distribute the package at `pypi`.

```
# create a repo named pypi-python
pmc repo create pypi-python python

# create a distro pypi that serves from a folder 'pypi'
pmc distro create pypi pypi pypi --repository pypi-python
```

### Packaging

1. Open up pyproject.toml file and confirm that the version field is correct.
2. If it's not correct, update it and open a new PR with your change.
3. In the cli directory, run `poetry build`.
4. Now proceed to the next section to upload your CLI package.

### Uploading

These steps assume that your pmc client is set up for the server from which you want to distribute
the pmc cli package.

```
PACKAGE_ID=$(pmc package upload dist/pmc_cli-0.0.1-py3-none-any.whl)

pmc repo packages update pypi-python --add-packages $PACKAGE_ID

pmc repo publish pypi-python
```
