# Migrate functions

These migration functions keep repo contents (ie packages) in sync between the csd.apt.linux app
(aka vCurrent) and the Compute-PMC app (aka v4/vNext).

There are three actions that are performed:

* When a package is added to a repo in vCurrent, vNext syncs in the repo's packages from vCurrent
* When a package is removed from a repo in vCurrent, the package gets removed from the vNext repo
* When a package is removed from a repo in vNext, the package gets removed from the vCurrent repo

We don't bother to add packages that get added to vNext to vCurrent.

There are two functions: a `queue_action` function that queues requests to add/remove packages in a
Service Bus Queue and a `process_action` function that reads the messages from the Service Bus and
processes them. The `process_action` will call the vnext or vcurrent API depending on what it needs
to do.

<pre>

vnext - - -
           | -> queue_action -> service bus -> process_action -> vnext/vcurrent
vcurrent  -

</pre>

## Service Bus

When a user adds and then removes a package for a vCurrent repo, these operations must be executed
the same order in vNext. The Azure Functions maintain this order by using a Service Bus Queue (which
guarantees ordering unlike a Storage Queue), and by limiting the processing function to a single
instance by setting `maxConcurrentCalls` and `WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT` both to 1.

## Azure CLI and Azure Functions CLI

In order to publish or run these functions locally, you'll need to [install the Azure Functions
CLI](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local). You may also need
to [install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) to publish
as well.

To set these up in a Python virtual environment, run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install azure-cli
pip install -r requirements.txt
```

## Running locally

While the Azure Functions can be run locally, [the Service Bus
cannot](https://github.com/Azure/azure-service-bus/issues/223). I recommend setting up a service bus
in Azure (see the Service Bus section) and then running the Functions locally.

To create a service bus using the Azure CLI, run:

```bash
rg="mypmcmigrate"
az group create --name $rg --location eastus
az servicebus namespace create --resource-group $rg --name pmcmigrate
az servicebus queue create --resource-group $rg --namespace-name pmcmigrate --name pmcmigrate --max-delivery-count 3 --lock-duration PT5M
az servicebus namespace authorization-rule keys list --resource-group $rg --namespace-name pmcmigrate --name RootManageSharedAccessKey --query primaryConnectionString --output tsv
```

The last command will output the service bus connection string. Copy `local.settings.json.example`
to `local.settings.json` and fill in `AzureServiceBusConnectionString` with your service bus
connection string.

Next set up your `config.sh` by copying one of the templates such as `config.sh.example` to
`config.sh` and filling in the values.
You can use `config.sh.local` which will automatically load your MSAL variables vnext
from your cli's settings.toml.
However, this won't work if you have multiple profiles set up in which case you can use
`config.sh.example` to manually define your MSAL variables.

Once your config.sh file is set up, source it:

```bash
source config.sh
```

Finally, run the Function App:

```bash
func start
```

Grab the url for the queue\_action function (should be something like
`http://localhost:7071/api/queue_action`) and fill it in for `AF_QUEUE_ACTION_URL` in your vnext
.env file and `afQueueActionUrl` for your vcurrent environment's confg.js file.

You can also debug by making requests directly via httpie:

```bash
http :7071/api/queue_action action_type=add source=vcurrent repo_name=debtest repo_type=apt release=bionic component=asgard packages:='[{"name": "aadlogin-selinux", "version": "1.0.016050002", "arch": "amd64"}]'
http :7071/api/queue_action action_type=remove source=vcurrent repo_name=debtest repo_type=apt release=bionic component=asgard packages:='[{"name": "aadlogin-selinux", "version": "1.0.016050002", "arch": "amd64"}]'
```

If you get a 403 response from vnext, make sure the account you're using has the Migration role.

### Testing

If you want to test out the Azure functions, you'll need to set up two repos--one in vNext and one
in vCurrent.

First though, you must serve the packages from vcurrent. Set up a python http server:

```bash
cd /var/lib/azure-aptcatalog
python3 -m http.server 8888
```

Now on vcurrent, set up some repos:

```bash
repoclient repo add -l debtest apt admin
repoclient repo add -l yumtest apt admin
```

You should be able to curl the repo dirs e.g. `curl http://localhost:8888/repos/debtest/`.

On vNext set up your repos and point to the vcurrent urls:

```bash
vcurrent="http://vcurrent:8888/"
pmc remote create debtest-apt apt "${vcurrent}repos/debtest" --distributions bionic
pmc repo create debtest-apt apt --remote debtest-apt --paths debtest
pmc remote create yumtest-yum yum "${vcurrent}repos/yumtest"
pmc repo create yumtest-yum yum --remote yumtest-yum --paths yumtest
```

Now back on vcurrent, try adding a package. You'll need the repo id (see `repoclient repo list`):

```bash
curl -O https://packages.microsoft.com/ubuntu/18.04/prod/pool/main/a/aadlogin-selinux/aadlogin-selinux_1.0.004850001_amd64.deb
repoclient package add -r 634edfb182695c71fa630531 aadlogin-selinux_1.0.004850001_amd64.deb
```

The package should now show up in `debtest-apt` on vnext. Check the function app output for any
messages.

## Publishing

In order to publish, you'll need to install the Azure CLI and the Azure Functions CLI. See the
section of this document about how to install these.

Then run the deploy script with your desired config.sh file:

```bash
./deploy.sh config.sh.ppe
```

If you need to re-publish the function code after you have deployed the app, you can run:

```bash
source config.sh.ppe
func azure functionapp publish ${resourceGroup}app --python --build remote
```

### Publishing to tux-dev

Because the function app in tux-dev has restricted network access, you'll have to deploy from a
server that can access it such as tux-ingest1. You'll also want to make sure that the hostname
pmc-tux-migrateapp.scm.azurewebsites.net resolves to the function app ip. This has been hardcoded in
the hosts file on tux-ingest1 already.
