Tux-Sync
===========
Tux-Dev (tux-devrepo.corp.microsoft.com) resides within Corpnet via ExpressRoute.
This imposes various network restrictions, particularly around public IP's,
which make it incompatible with some of our core technologies (AKS, Postgres, and 
Service Bus). As a workaround, the vNext/Pulp instance of tux-dev is hosted in
two IAAS VM's in Expressroute, using a setup that is very similar to our dev 
environment. The tools in this directory are used for deploying these instances
and keeping them in sync as things change over time.

### `tux-sync.py`
The "one-stop" tool for synchronizing a tux-dev vNext VM. This tool will
    - Fetch latest secrets from KeyVault
    - Fetch latest container images from ACR
    - Install the latest nginx config (for TLS termination)
    - Recycle containers via `docker compose`

### Environment (.env) Files
Without AKS to manage our environment, we rely on `.env` files to configure our apps.
These should be self-explanatory based on their filenames.

### `docker-compose.yml`
Defines how the containers are hosted and their network connections.
This is derived from, and strongly resembles, our dev environment.

### nginx
In order to serve the PMC API over HTTPS/TLS, we need a TLS termination solution.
In this case, we use NGINX, which proxies requests for the PMC API. This depends on 1 file: `nginx/ssl.conf`. This is mounted to a running NGINX container under `/etc/nginx`.
