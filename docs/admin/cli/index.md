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
cd cli
poetry install --with dev --extras pygments
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

Some default Service Principals are available to simplify your dev environment
1. Run `make config`
  - This will generate a config in the default location (~/.config/pmc/settings.toml)
  - It will prepopulate this config file with the necessary settings.
2. Download the latest PEM file from [Azure Keyvault](https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/asset/Microsoft_Azure_KeyVault/Certificate/https://mb-repotest.vault.azure.net/certificates/esrp-auth-test) and place it in `~/.config/pmc/auth.pem`
3. The default user's role is a Repo_Admin. There are also other role-based account profiles available: `--profile [account|repo|package|publisher]`

## Testing

In order to run the tests, you'll need to set up a settings.toml for the test environment. From your
cli directory, run the following command. Then open the tests/settings.toml file to make any
necessary changes based on your setup.

```
make tests/settings.toml
```

After that, you can run all your tests or lint the code:

```
make test
make lint
```

You can also run an individual test with pytest:

```
pytest tests/commands/test_package.py::test_invalid_deb_package_upload
```

## Changelog entries

To manage the changelog for the cli, we use [towncrier](https://github.com/twisted/towncrier). For
every change that impacts publishers, a new changelog entry should be accompanied with the change.
To create a changelog entry, create a file in the `cli/changelog.d` folder with the issue number and
an extension of:

* **.feature** - new features
* **.bugfix** - bug fixes
* **.breaking** - breaking changes

As an example, if I am fixing issue
[17315271](https://msazure.visualstudio.com/One/\_workitems/edit/17315271/), I'd create a
`cli/changelog.d/17315271.feature` file with the text "Added a feature that allows publishers to
upload a directory of packages".

Some things to note:

* The changelog and changelog entries support markdown.
* The changelog (`cli/CHANGELOG.md`) gets updated before each release from the entries in
  changelog.d
* Unlike commit messages, the primary audience for the changelog is users.
* It's possible to have multiple changelog entry types for a single issue (e.g. if you have a bug
  fix that includes a breaking change, you'd create .bugfix file and a .breaking file).


## Workflows

Once you've set up the server and CLI, view the `docs/admin/workflows.md` file for some example
workflows.
