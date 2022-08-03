# pmc_scan_mirrors function app (readme)

## Summary

Scans all of the PMC mirrors and is triggered by a timer every 3 minutes. Results are added to the results-queue (an Azure storage queue) which triggers a function in **pmc_status_delivery** to publish the results.

## Function details
### generate_mirror
Takes a list of mirrors from a blob and adds them to the mirror-request-queue for them to be checked. 

- **trigger**: Timer every 3 minutes.

- **inputs**: 
    
    inputblobmirrors - JSON blob that contains a list of mirrors. The content of the blob is located in 'static-data/mirrors.json' in the storage account connection string pmcstatusprimary_CONNECTION.

- **outputs**:

    mirror-request-queue - Mirror urls are added to this storage queue and check_mirror will dequeue and check the availability of each mirror.

    results-queue - A list of mirrors is sent to the results queue so that should a mirror be removed, the status JSON will also have the mirror removed from its list. 

### check_mirror
Checks mirrors in the message queue. 

- **trigger**: Messages in the Azure storage queue *mirror-request-queue*. 

- **inputs**: None

- **outputs**: 
    
    results-queue - The status of each mirror is added to the results queue for publishing. 

## Function app Configuration
### - `host.json` 

We want mirrors to be checked in parallel so the queue settings and scale out are configured for parallelism. 
- ***batchisze = 16*** so that 16 mirrors are dequeued at a time and checked in parallel. 

- ***newBatchThreshold = 8*** so once there are only 8 mirrors being checked at a given time, another batchSize (16) will be dequeued. This means 24 mirrors can be checked at a time by a single instance. 

- ***maxDequeueCount = 3*** means the function can fail 3 times until the message moved to a poison queue. 

### - Portal settings
This function should be in a **Consumption Plan**. In Setting->Configuration->Application settings the following values must be configured.

- **AzureWebJobsStorage**: Storage account connection string the function requires to run. This is where temporary files and other function file are stored. Each function app should have its own storage account. 

- **pmcstatusprimary_CONNECTION**: pmcstatusprimary storage account connection string detailed in this [readme](../../README.md). This setting should be same across pmc_scan_repos, pmc_scan_mirrors, and pmc_status_delivery. 

Lastly, the **Scale Out** setting should be set as follows to allow for scale out when needed. Azure Functions will determine how many instances are needed given the current load. Leaving `Maximum Scale Out Limit` at a large value means that we give Azure Functions the maximum ability to scale out even though no more than a few instances may be needed for pmc_scan_mirrors. 

- Enforce Scale Out Limit: Yes
- Maximum Scale Out Limit: 200 (This is whatever the current default value is for an Azure Function app running in a consumption plan.)