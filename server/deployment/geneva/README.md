# Geneva Setup
The things in this directory exist for the purpose of setting up logs/metrics streaming into
Geneva, and so are likely only applicable in Prod and only needed for a 1-time setup.

## Querying
Logs are being streamed to DGrep.
To query, go to [the DGrep portal](https://portal.microsoftgeneva.com/logs/dgrep), select
`endpoint` -> `Diagnostics PROD` and `namespace` -> `PMClogs`.
Select the "events" of the types of containers you're interested in, and the appropriate time
filter.
Note that logs are "live" but on about an inconsistent 1-15-minute delay.

## Setup in AKS
These configs create a `geneva` namespace and then set up some containers that run as a daemon in
AKS.
They can be viewed in the webui by going to `Workloads` -> `Daemon Sets` -> `geneva-services`.
They can be managed in the cli by specifying namespace:
`kubectl logs --namespace geneva geneva-services-dtpmq -c fluentd --tail=10`.

## Configuration
See [the Geneva documentation](https://eng.ms/docs/products/geneva/getting_started/environments/akslinux)
for more information.
In brief we are configuring `fluentd` to read the kubernetes log files, tag them by container type,
and send them to `mdsd`.
`mdsd` then streams those logs to Geneva.
Geneva is configured via the xml file to put tagged logs in the appropriate tables.
The `mdm` container is for streaming metrics.
See [this doc](https://eng.ms/docs/products/geneva/collect/instrument/linux/fluentd) for more info
on possible `fluentd` configurations.

The files in `helm/` were copied wholesale out of [their example](https://msazure.visualstudio.com/One/_git/Compute-Runtime-Tux-GenevaContainers?path=/docker_geneva_samples/AKSGenevaSample/Deployment/Geneva)
and then modified with our values.
Specifically, the only files that were edited were:
1. `helm/pmc-prod.values.yml`, which contains our deployment-specific variables
1. `helm/PMClogsVer1v0.xml`, which is a copy of the PMClogs configuration
    [in Jarvis](https://portal.microsoftgeneva.com/manage-logs-config?endpoint=Diagnostics%2520PROD&gwpAccount=PMClogs&configId=PMClogsVer1v0&gcsEnabled=true&gsmEnabled=true).
1. `helm/fluentd.conf`, where we define our tags for the different containers so Geneva can put them
    in the appropriate tables.

## Helm
The problem with using `helm` to template the yml files is that `helm` itself is a little hard to
source on the pmc-deploy machine.
[You can](https://helm.sh/docs/intro/install/):
1. Stream a random install script off the internet straight into bash. 🤮
1. Install a random deb signed by a random key. 🙄
1. Install a random community-maintained snap. 😔

Let's not install helm at this time.
Instead, since this should indeed be a 1-time setup, I'll simply "de-template" the yaml files and
pass them to `kubectl` like we do everything else.
This leads to the creation of the two top-level yml files.

## De-templated Files
### fluentd_configs.yaml
This simply writes the not-additionally-modified `helm/fluentd.conf` and
`helm/chart/fluentd/kubernetes.conf` configs into the ConfigMap.
I separated them out into their own file because they are fairly large.
This should be defined with `kubectl` _first_.

### geneva.<env>.yaml
This is all the rest of the stuff that would be defined in
`helm/chart/templates/geneva-services.yaml`, but with the values from `helm/pmc-<env>.values.yaml`
filled in and choosing which "if" blocks to keep appropriately:
1. Yes we're using csiSecretProvider to sync the cert from the keyvault.
1. No, don't try to install azSecPack on the nodes.
   Their container that does this only works with Ubuntu Nodes (we use Mariner).
   And we already have azSecPack running anyway, so we don't need this container.
1. No, because this is a prod environment we do not have a different metricEndpoint.
