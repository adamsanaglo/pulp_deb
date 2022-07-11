.PHONY: lint tests
msal_client_id ?= "c93b1ed1-3b3e-408c-9003-10c87975644a"
msal_scope ?= "api://1ce02e3e-1bf3-4d28-8cdc-e921f824399d/.default"
msal_cert_path ?= "${HOME}/.config/pmc/auth.pem"
msal_authority ?= "https://login.microsoftonline.com/Microsoft.onmicrosoft.com"
config_file ?= "${HOME}/.config/pmc/settings.toml"

lint:
	flake8 .
	isort -c .
	black --check .
	mypy .

format:
	isort .
	black .

tests/settings.toml:
	cp tests/assets/settings.example.toml tests/settings.toml

test: tests/settings.toml
	pytest

config:
	pmc config create --no-edit
	@sed -i 's#msal_client_id = ""#msal_client_id = ${msal_client_id}#' ${config_file}
	@sed -i 's#msal_scope = ""#msal_scope = ${msal_scope}#' ${config_file}
	@sed -i 's#msal_cert_path = ""#msal_cert_path = ${msal_cert_path}#' ${config_file}
	@sed -i 's#msal_authority = ""#msal_authority = ${msal_authority}#' ${config_file}
