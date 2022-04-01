.PHONY: lint tests

lint:
	flake8 .
	isort -c .
	mypy .

make tests:
	pytest
