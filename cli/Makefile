.PHONY: lint tests

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
