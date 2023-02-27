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

## Workflows

Once you've set up the server and CLI, view the `docs/admin/workflows.md` file for some example
workflows.
