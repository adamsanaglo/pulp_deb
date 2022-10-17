# settings for pulp that get mounted into Pulp's containers
CONTENT_ORIGIN = "http://localhost:8081"
PYPI_API_HOSTNAME = "http://localhost:8081"
TOKEN_AUTH_DISABLED = True
TELEMETRY = False
CONTENT_PATH_PREFIX = "/"

# pulp_deb settings
PUBLISH_RELEASE_FILE_LABEL = True
