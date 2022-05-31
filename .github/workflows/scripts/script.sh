#!/usr/bin/env bash
# coding=utf-8

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_deb' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..
REPO_ROOT="$PWD"

set -mveuo pipefail

source .github/workflows/scripts/utils.sh

export POST_SCRIPT=$PWD/.github/workflows/scripts/post_script.sh
export POST_DOCS_TEST=$PWD/.github/workflows/scripts/post_docs_test.sh
export FUNC_TEST_SCRIPT=$PWD/.github/workflows/scripts/func_test_script.sh

# Needed for both starting the service and building the docs.
# Gets set in .github/settings.yml, but doesn't seem to inherited by
# this script.
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
export PULP_SETTINGS=$PWD/.ci/ansible/settings/settings.py

export PULP_URL="https://pulp"

if [[ "$TEST" = "docs" ]]; then
  if [[ "$GITHUB_WORKFLOW" == "Deb CI" ]]; then
    pip install towncrier==19.9.0
    towncrier --yes --version 4.0.0.ci
  fi
  cd docs
  make PULP_URL="$PULP_URL" diagrams html
  tar -cvf docs.tar ./_build
  cd ..

  if [ -f $POST_DOCS_TEST ]; then
    source $POST_DOCS_TEST
  fi
  exit
fi

if [[ "${RELEASE_WORKFLOW:-false}" == "true" ]]; then
  STATUS_ENDPOINT="${PULP_URL}${PULP_API_ROOT}api/v3/status/"
  echo $STATUS_ENDPOINT
  REPORTED_VERSION=$(http $STATUS_ENDPOINT | jq --arg plugin deb --arg legacy_plugin pulp_deb -r '.versions[] | select(.component == $plugin or .component == $legacy_plugin) | .version')
  response=$(curl --write-out %{http_code} --silent --output /dev/null https://pypi.org/project/pulp-deb/$REPORTED_VERSION/)
  if [ "$response" == "200" ];
  then
    echo "pulp_deb $REPORTED_VERSION has already been released. Skipping running tests."
    exit
  fi
fi

if [[ "$TEST" == "plugin-from-pypi" ]]; then
  COMPONENT_VERSION=$(http https://pypi.org/pypi/pulp-deb/json | jq -r '.info.version')
  git checkout ${COMPONENT_VERSION} -- pulp_deb/tests/
fi

echo "machine pulp
login admin
password password
" | cmd_stdin_prefix bash -c "cat > /root/.netrc"

cat unittest_requirements.txt | cmd_stdin_prefix bash -c "cat > /tmp/unittest_requirements.txt"
cat functest_requirements.txt | cmd_stdin_prefix bash -c "cat > /tmp/functest_requirements.txt"
cmd_prefix pip3 install -r /tmp/unittest_requirements.txt
cmd_prefix pip3 install -r /tmp/functest_requirements.txt
cmd_prefix pip3 install --upgrade ../pulp-smash

cd ../pulp-openapi-generator
./generate.sh pulp_deb python
cmd_prefix pip3 install /root/pulp-openapi-generator/pulp_deb-client
sudo rm -rf ./pulp_deb-client
./generate.sh pulpcore python
cmd_prefix pip3 install /root/pulp-openapi-generator/pulpcore-client
sudo rm -rf ./pulpcore-client
cd $REPO_ROOT

CERTIFI=$(cmd_prefix python3 -c 'import certifi; print(certifi.where())')
cmd_prefix bash -c "cat /etc/pulp/certs/pulp_webserver.crt  | tee -a "$CERTIFI" > /dev/null"

# check for any uncommitted migrations
echo "Checking for uncommitted migrations..."
cmd_prefix bash -c "django-admin makemigrations --check --dry-run"

if [[ "$TEST" != "upgrade" ]]; then
  # Run unit tests.
  cmd_prefix bash -c "PULP_DATABASES__default__USER=postgres pytest -v -r sx --color=yes -p no:pulpcore --pyargs pulp_deb.tests.unit"
fi

# Run functional tests
if [[ "$TEST" == "performance" ]]; then
  if [[ -z ${PERFORMANCE_TEST+x} ]]; then
    cmd_prefix bash -c "pytest -vv -r sx --color=yes --pyargs --capture=no --durations=0 pulp_deb.tests.performance"
  else
    cmd_prefix bash -c "pytest -vv -r sx --color=yes --pyargs --capture=no --durations=0 pulp_deb.tests.performance.test_$PERFORMANCE_TEST"
  fi
  exit
fi

if [ -f $FUNC_TEST_SCRIPT ]; then
  source $FUNC_TEST_SCRIPT
else

    if [[ "$GITHUB_WORKFLOW" == "Deb Nightly CI/CD" ]]; then
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m parallel -n 8 --nightly"
        cmd_prefix bash -c "pytest -v -r sx --color=yes --pyargs pulp_deb.tests.functional -m 'not parallel' --nightly"

    
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulpcore.tests.functional -m 'from_pulpcore_for_all_plugins and parallel' -n  8 --nightly"
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulpcore.tests.functional -m 'from_pulpcore_for_all_plugins and not parallel'  --nightly"
    
    else
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m parallel -n 8"
        cmd_prefix bash -c "pytest -v -r sx --color=yes --pyargs pulp_deb.tests.functional -m 'not parallel'"

    
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulpcore.tests.functional -m 'from_pulpcore_for_all_plugins and parallel' -n  8"
        cmd_prefix bash -c "pytest -v -r sx --color=yes --suppress-no-test-exit-code --pyargs pulpcore.tests.functional -m 'from_pulpcore_for_all_plugins and not parallel'"
    
    fi

fi

if [ -f $POST_SCRIPT ]; then
  source $POST_SCRIPT
fi