## Config

Users can configure their cli clients with a config file. To create a new config file, see `pmc
config create --help`. Users can also edit an existing config file with `pmc config edit`.

Supported formats are json and toml, and must be stored in either a file ending in `.json` or
`.toml` respectively.

By default, pmc cli will look for a config file in the user's config path. The path depends on the
OS but `pmc --help` will show the default locations.

The config file location may also be specified by setting an environment variable (`PMC_CLI_CONFIG`)
or setting `--config` when running pmc (ie `pmc --config ~/settings.toml ...`).

## Dev Environment

First, install poetry via pipx:

```
pip install pipx
pipx install poetry
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

## Example Workflow

```
# create a repo
REPO_ID=$(pmc --id-only repo create myrepo apt)

# create a distro
pmc distro create mydistro apt "some/path" --repository $REPO_ID

# upload a package
wget https://packages.microsoft.com/repos/cbl-d/pool/main/v/vim/vim-common_8.1.0875-5_all.deb
PACKAGE_ID=$(pmc --id-only package upload vim-common_8.1.0875-5_all.deb)

# add our package to the repo
pmc repo packages update $REPO_ID --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish $REPO_ID

# check out our repo
http :8080/pulp/content/some/path/
```
