# /edge tools and scripts

The contents of this directory apply to the PMC edge content delivery infrastructure.
Some scripts are intended to be executed from the jumpbox under the apt-automation user; others are deployed to and executed on the edge servers.
The log analyzer can be run from either the jumpbox or from an edge server; some analysis modes change or are unavailable depending on where the tool is run.

## Jumpbox tools

Tools on the jumpbox fall into these buckets:

1) Deploying scripts to edge servers
1) Managing edge server configuration

For all edge tools, "target" can be:

- an individual server name (e.g. `euap1`)
- an edge region (e.g. `wus`)
- the string `all` signifying all servers in all regions

### Edge deployment scripts

```bash
deploy_fetcher.sh [--prereqs] target
```

Deploy "APT metadata fetcher" scripts and configs to the target.
If `--prereqs` is specified, required apt and python packages are installed and configured before the fetcher components are deployed.

### Edge configuration tools

```bash
push-config.sh mode path target
```

Push the nginx configuration file for vnext or vcurrent (the `mode` parameter), found in local file `path`, to the target.
The local file will be installed in /etc/nginx/sites-available/*mode* on the target and will not be made the active configuration.

```bash
flip-mirrors.sh mode sha256sum target
```

Enable the indicated PMC mode (vnext or vcurrent) on the target by copying the relevant already-pushed configuration from /etc/nginx/sites-available to /etc/nginx/sites-enabled.
The second parameter is the SHA-256 checksum of the config file the user believes has already been pushed to the target; if the checksum doesn't match, the edge server will not be affected.

```bash
force-meta-update.sh target
```

Set a flag on the target such that the next APT metadata update cycle will do a "--force" update, pulling all metadata files whether the origin metadata is newer or not.

## Edge scripts

Scripts on edge servers fall in three buckets:

1) Scripts invoked by tools running on the jumpbox
1) Scripts triggered by cron jobs
1) Monitoring scripts to be run on the server or from the jumpbox remotely

### Remotely invoked scripts (installed in ~apt-automation)

- `config-activate.sh` changes the enabled nginx config and restarts nginx.
- `config-install.sh` is obsolete; it was used for initial deployment of the vNext config on the edge mirrors.

### Scripts triggered by cron

- crontab is deployed to /etc/cron.d/update_meta. It invokes update_meta.sh as user www-data every 5 minutes.
- update_meta.sh is deployed to /var/pmc. It refreshes /var/pmc/apt-repos.txt, then invokes fetch-apt-metadata.py on each pocket.
- fetch-apt-metadata.py updates the locally-cached metadata for a pocket.

### Monitoring scripts

```bash
watch.sh 404|access|dist|fetch
```

Watches log files in realtime for particular events.

- `404` watches the nginx access log for 404 replies (filtering out obviously bad requests). This is pretty noisy.
- `access` watches the nginx access log without any filtering
- `dist` watches the nginx access log for non-successful requests for APT metadata (not in 200, 206, 304).
- `fetch` watches syslog for messages emitted by the APT metadata fetcher.

## Log analysis via log-analyze

```
usage: log-analyze [-h] [--start-time START_TIME] [--view-status VIEW_STATUS] [--view-filter VIEW_FILTER]
                   [--view-unparseable] [--view-404] [--json] [--verbose] [-v]
                   [logfiles ...]


Analyze PMC nginx logs.

positional arguments:
  logfiles              Log files to analyze. Format is [host:]name where host
                        specifies an ssh-accessible server and name is either
                        absolute or relative to /var/log/nginx. Default is
                        'access.log'.

options:
  -h, --help            show this help message and exit
  --start-time START_TIME
                        ISO 8601 datetime before which log records are ignored.
  --view-status VIEW_STATUS
                        View requested URIs receiving a specific status code.
  --view-filter VIEW_FILTER
                        Ignore URIs (returned by --view-status) matching this regex.
  --view-unparseable
  --view-404
  --json
  --verbose
  -v, --version         show program's version number and exit
```