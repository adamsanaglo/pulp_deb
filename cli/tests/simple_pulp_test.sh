#!/bin/bash

./update_role.sh Package_Admin
PACKAGE_ID=$(poetry run pmc --id-only package upload tests/assets/signed-by-us.rpm)

./update_role.sh Repo_Admin
REPO_ID=$(poetry run pmc --id-only repo create test_repo yum)
poetry run pmc repo packages update $REPO_ID --add-packages $PACKAGE_ID
poetry run pmc repo publish $REPO_ID
poetry run pmc distro create test-distro yum test-repo --repository $REPO_ID
