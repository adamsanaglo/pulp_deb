.PHONY: lint tests
msal_client_id ?= c93b1ed1-3b3e-408c-9003-10c87975644a
msal_scope ?= api://1ce02e3e-1bf3-4d28-8cdc-e921f824399d/.default
msal_cert_path ?= ${HOME}/.config/pmc/auth.pem
msal_authority ?= https://login.microsoftonline.com/Microsoft.onmicrosoft.com
config_file ?= ${HOME}/.config/pmc/settings.toml
signing_service ?= legacy

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
	pmc config create --no-edit \
		--location "${config_file}" \
		--msal-client-id "${msal_client_id}" \
		--msal-scope "${msal_scope}" \
		--msal-cert-path "${msal_cert_path}" \
		--msal-authority "${msal_authority}" \
		--signing-service "${signing_service}" \
		--show-restricted-commands
	@echo "Created ${config_file}"
