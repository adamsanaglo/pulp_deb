# settings for pulp that get mounted into the pulp single container
CONTENT_ORIGIN = "http://$(hostname):8080"
ANSIBLE_API_HOSTNAME = "http://$(hostname):8080"
ANSIBLE_CONTENT_HOSTNAME = "http://$(hostname):8080/pulp/content"
TOKEN_AUTH_DISABLED = True
