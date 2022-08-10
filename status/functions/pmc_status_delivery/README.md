# pmc_status_delivery function app (readme)

## Summary

The one function in this app, **publish_status_result**, is triggered by messages added to the results-queue. Publishes mirror and repository status to a JSON blob which is then read by the website. 

## Function details
### publish_status_result
Publishes multiples batches of mirror and repository status messages to a single status JSON. 

- **trigger**: Messages in the Azure storage queue *results-queue*. 

- **inputs**: None

- **outputs**: None

## Function app Configuration
### - `host.json` 

Careful thought was placed into the queue settings. We want only one function call to be running at a time. That function will be triggered by a single message in the *results-queue* but will dequeue multiple messages in the queue to publish.

- ***batchsize = 1*** so only 1 function call is triggered even when multiple messages are in the *results-queue*.

- ***newBatchThreshold = 0*** so that new messages aren't dequeued until the previous function call finishes.

- ***maxDequeueCount = 5*** means the function can fail 5 times until the message moves to a poison queue. This behavior is also mimicked in the function code for messages manually dequeued from the *results-queue*.

### - Portal settings
This function should be in a **Consumption Plan**. In Setting->Configuration->Application settings the following values must be configured.

- **AzureWebJobsStorage**: Storage account connection string the function requires to run. This is where temporary files and other function file are stored. Each function app should have its own storage account. 

- **pmcstatusprimary_CONNECTION**: pmcstatusprimary storage account connection string detailed in this [readme](../../README.md). This setting should be same across pmc_scan_repos, pmc_scan_mirrors, and pmc_status_delivery. 

- **JsonContainerName**: Name of the container in pmcstatusprimary_CONNECTION that contains the status JSON.

- **JsonBlobName**: Name of the blob in the WebsiteContainer that contains the status JSON. 

- **ResultsQueueName**: Name of the results queue which should be "results-queue". Set the same as the "queueName" entry in `publish_status_result/function.json`. 

Lastly, the **Scale Out** setting should be set as follows so that there is ever only one instance of the function app running at time. This single instance will have at most one function call running at a time.

- Enforce Scale Out Limit: Yes
- Maximum Scale Out Limit: 1