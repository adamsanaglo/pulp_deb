# pmc_status_delivery function app (readme)

## Summary

The one function in this app, **publish_status_result**, is triggered by messages added to the results-queue. Publishes mirror and repository status to a JSON blob which is then read by the website. 

## Function details
### publish_status_result
Publishes mirror and repository status messages to a single status JSON. 

- **trigger**: Messages in the Azure storage queue *results-queue*. 

- **inputs**: None

- **outputs**: None

## Function app Configuration
### - `host.json` 

Careful thought was placed into the queue settings. The primary bottleneck in this
function app is that an exclusive lease has to be obtained on the status JSON before
it is read and updated. This makes the function highly sequential. However, through
some benchmarking, it was observed that there is still some benefit to having a
small amount of parallelism. 
- ***batchsize = 6*** so that 6 status messages are dequeued and published at at the same time.

- ***newBatchThreshold = 0*** so that new messages aren't dequeued until the previous 6 finished publishing, this ensures that there is minimal starvation in the parallel setting. 

- ***maxDequeueCount = 5*** means the function can fail 5 times until the message moved to a poison queue. 

### - Portal settings
This function should be in a **Consumption Plan**. In Setting->Configuration->Application settings the following values must be configured.

- **AzureWebJobsStorage**: Storage account connection string the function requires to run. This is where temporary files and other function file are stored. Each function app should have its own storage account. 

- **pmcstatusprimary_CONNECTION**: pmcstatusprimary storage account connection string detailed in this [readme](../../README.md). This setting should be same across pmc_scan_repos, pmc_scan_mirrors, and pmc_status_delivery. 

- **JsonContainerName**: Name of the container in pmcstatusprimary_CONNECTION that contains the status JSON.

- **JsonBlobName**: Name the blob in the WebsiteContainer that contains the status JSON. 

Lastly, the **Scale Out** setting should be set as follows so that there is ever only one instance of the function app running at time. This single instance will process 6 messages at once.

- Enforce Scale Out Limit: Yes
- Maximum Scale Out Limit: 1