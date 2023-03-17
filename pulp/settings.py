# settings for pulp that get mounted into Pulp's development containers
# any setting here will not affect deployments and will most likely also need to be set in
# server/deployment/config.yml

CONTENT_ORIGIN = "http://localhost:8081"
PYPI_API_HOSTNAME = "http://localhost:8081"
TOKEN_AUTH_DISABLED = True
TELEMETRY = False
CONTENT_PATH_PREFIX = "/"

# pulp_deb settings
PUBLISH_RELEASE_FILE_LABEL = True

# pulp_rpm settings
RPM_METADATA_USE_REPO_PACKAGE_TIME = True
