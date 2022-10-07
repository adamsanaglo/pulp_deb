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
processes them.

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

```
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

```
rg="mypmcmigrate"
az group create --name $rg --location eastus
az servicebus namespace create --resource-group $rg --name pmcmigrate
az servicebus queue create --resource-group $rg --namespace-name pmcmigrate --name pmcmigrate --max-delivery-count 3
az servicebus namespace authorization-rule keys list --resource-group $rg --namespace-name pmcmigrate --name RootManageSharedAccessKey --query primaryConnectionString --output tsv
```

The last command will output the service bus connection string. Copy `local.settings.json.example`
to `local.settings.json` and fill in `AzureServiceBusConnectionString` with your service bus
connection string.

Then copy `config.sh.local` to `config.sh`, fill in any variables, and then run:

```
source config.sh
```

Finally, run the Function App:

```
func start
```

Grab the url for the queue\_action function (should be something like
`http://localhost:7071/api/queue_action`) and fill it in for `AF_QUEUE_ACTION_URL` in your vnext
.env file and `afQueueActionUrl` for your vcurrent environment's confg.js file.

You can also debug by making requests directly via httpie:

```
http :7071/api/queue_action action_type=remove source=vcurrent repo_name=test repo_type=apt release=nosuite component=asgard "package[name]=thor" "package[version]=1.0" "package[arch]=ppc64"
```

If you get a 403 response from vnext, make sure the account you're using has the Migration role.

## Publishing

In order to publish, you'll need to install the Azure CLI and the Azure Functions CLI. See the
section of this document about how to install these.

Next copy `config.sh.example` to `config.sh` and fill in the latter if you haven't already.

Then run the deploy script:

```
./deploy.sh
```
