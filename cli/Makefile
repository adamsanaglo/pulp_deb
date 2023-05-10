.PHONY: lint tests
SHELL = bash
.ONESHELL:
repo_client_id ?= c93b1ed1-3b3e-408c-9003-10c87975644a
account_client_id ?= a30dc6a5-6c11-4478-8fec-c9aa19705434
package_client_id ?= cb1695a3-45dd-43b9-9b32-3d9b7c32e994
publisher_client_id ?= 2ea13e79-0a4f-4650-9816-91bb798f0bd7
msal_scope ?= api://1ce02e3e-1bf3-4d28-8cdc-e921f824399d/.default
msal_cert_path ?= ${HOME}/.config/pmc/auth.pem
msal_authority ?= https://login.microsoftonline.com/Microsoft.onmicrosoft.com
config_file ?= ${HOME}/.config/pmc/settings.toml
signing_service ?= legacy
base_url = http://localhost:8000/api/v4

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
		--base-url "${base_url}" \
		--location "${config_file}" \
		--msal-client-id "${repo_client_id}" \
		--msal-scope "${msal_scope}" \
		--msal-cert-path "${msal_cert_path}" \
		--msal-authority "${msal_authority}" \
		--signing-service "${signing_service}" \
		--show-restricted-commands
	cat <<- EOF >> ~/.config/pmc/settings.toml
		
		[repo]
		# The default user is already a Repo_Admin
		
		[account]
		msal_client_id = "${account_client_id}"
		
		[package]
		msal_client_id = "${package_client_id}"
		
		[publisher]
		msal_client_id = "${publisher_client_id}"
	EOF
	@echo "Created ${config_file}"
