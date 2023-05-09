#!/bin/bash

PACKAGE_ID=$(poetry run pmc --id-only --profile package package upload tests/assets/signed-by-us.rpm)
REPO_ID=$(poetry run pmc --id-only repo create test_repo yum)
poetry run pmc repo packages update $REPO_ID --add-packages $PACKAGE_ID
poetry run pmc repo publish $REPO_ID
poetry run pmc distro create test-distro yum test-repo --repository $REPO_ID
