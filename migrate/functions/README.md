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

### Setting up a Service Bus

Follow [the Azure docs on how to set up a Service Bus
Queue](https://docs.microsoft.com/en-us/azure/service-bus-messaging/service-bus-quickstart-portal#create-a-namespace-in-the-azure-portal).
You can use any namespace name but the queue should be named `pmcmigrate`. After you create the
service bus, [get the connection
string](https://docs.microsoft.com/en-us/azure/service-bus-messaging/service-bus-quickstart-portal#get-the-connection-string)
which you'll need to connect to the service bus from the Azure functions.

You may also want to set the max delivery count which defaults to 10. This is set on the queue's
properties page and it controls how many times the `process_action` function will retry a message.
I'd probably recommend something like 2-5.

## Azure CLI and Azure Functions CLI

In order to publish or run these functions locally, you'll need to [install the Azure Functions
CLI](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local). You may also need
to [install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) to publish
as well.

## Running locally

While the Azure Functions can be run locally, [the Service Bus
cannot](https://github.com/Azure/azure-service-bus/issues/223). I recommend setting up a service bus
in Azure (see the Service Bus section) and then running the Functions locally.

First copy `local.settings.json.example` to `local.settings.json` and fill in
`AzureServiceBusConnectionString` with your service bus connection string.

```
python -m venv .venv
source .venv/bin/activate
pip install azure-cli
pip install -r requirements.txt
```

### Setting environment variables

Now export your env variables:

```
# URLS
export VNEXT_URL="http://localhost:8000"
export VCURRENT_SERVER="vcurrent"
export VCURRENT_PORT="8443"

# set vnext MSAL vars using the pmc settings file
for var in $(grep msal ~/.config/pmc/settings.toml | sed -e 's/^\(\S*\) = /\U\1=/'); do eval "export $var"; done

# manual setting of vnext MSAL vars
export MSAL_CLIENT_ID="<client id>"
export MSAL_SCOPE="<scope>"
export MSAL_CERT_PATH="<cert path>"
export MSAL_AUTHORITY="<authority>"
export MSAL_SNIAUTH="1"

# vcurrent AAD vars
export AAD_CLIENT_ID="<client id>"
export AAD_CLIENT_SECRET="<client secret>"
export AAD_CLIENT_RESOURCE="<client resource>"
export AAD_TENANT="<tenant>"
export AAD_AUTHORITY_URL="<authority url>"
```

### Run your Function App

Any finally, run the Function App:

```
func start
```

You can debug by making requests directly via httpie:

```
http :7071/api/queue_action action_type=remove source=vcurrent repo_name=test repo_type=apt release=nosuite component=asgard "package[name]=thor" "package[version]=1.0" "package[arch]=ppc64"
```

If you get a 403 response, make sure the account you're using has the correct role.

## Publishing

In order to publish, you'll need to install the Azure CLI and the Azure Functions CLI. See the
section of this document about how to install these.

First go to the Portal and [create an Azure Function
App](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-function-app-portal)
(but not an actual function). While in the Portal, also set up the Service Bus queue (see the
section of this doc on Setting up a service bus). Grab the Service Bus connection string.

In the settings page for your Azure Function App, set the settings defined in
`migrate/functions/localsettings.json.example` file (AzureServiceBusConnectionString, etc).
`AzureWebJobsStorage` doesn't need to be set unless you need to use storage. Also, set the
environment variables defined in the section of this document on Setting environment variables
(VNEXT_URL, VCURRENT_SERVER, etc).

In the migrate/functions directory of your local vnext checkout, log in with `az login` and then
run:

```
func azure functionapp publish <app name>
```

Go to the portal and on the "Code + Test" page for the queue_action function, click "Get function
URL" button and grab the function URL. Populate this URL in the `afQueueActionUrl` setting for
vcurrent and `AF_QUEUE_ACTION_URL` setting for vnext.
