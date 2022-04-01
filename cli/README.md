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
