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
msal_scope    |--msal-scope    | The scope for which a token will be requested (i.e. api://13ab6030 ...)
