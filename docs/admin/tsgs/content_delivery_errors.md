# Content Delivery Errors
This section summarizes issues that customers may raise regarding their ability to download our content.

## Apt/Deb Metadata Out of Date
**Symptom:** A package is visible in the repo, but not in the metadata.

**Resolution:** Refer to the [Deb Package Not Found in Metadata](deb_metadata.md) TSG.

## DNS Errors
**Symptom:** One or more customers indicate that they cannot resolve the hostname for packages.microsoft.com.

**Resolution:** There are multiple potential causes and courses of action.
1. Identify the scope of the failure.
    - Are several people/teams reporting the issue?
    - Are you able to reproduce the issue? Consider testing this in the same region as the customer.
        ```bash
        $ nslookup packages.microsoft.com
        ```
2. If there are 3 or more reports of this issue, or if you can repro the issue yourself, file an IcM on behalf of our users and track it to completion.
    - Review the escalation TSG at https://aka.ms/adricm
    - [Generate an IcM](https://portal.microsofticm.com/imp/v3/incidents/create) for **Cloudnet / DNS Recursive**
3. If you *cannot* repro the issue *and* there are fewer than 3 reports of this issue, advise the customer to troubleshoot further.
    - If they're internal to MSFT, they can review https://aka.ms/adricm and  [generate an IcM](https://portal.microsofticm.com/imp/v3/incidents/create) for **Cloudnet / DNS Recursive**
    - Recommend they use nslookup, dig, and similar tools to troubeshoot further
    - In many cases, this is due to networking in a container environment, which can block some network activity.
    - Bottom line: PMC doesn't run the DNS service.
    If our DNS records are correct, there's little more we can do.

## Connection Timeout
**Symptom:** Customer indicates that they receive a connection timeout connecting to packages.microsoft.com.

**Resolution:** While rare, this could indicate that our servers are experiencing high load.
1. Determine which region/mirrors are affected.
    - This can be determined by asking the customer to run `nslookup packages.microsoft.com` and correlating the results to our [list of mirrors](edge_cache.md).
    - Login to a mirror in the affected region.
    - Run `sudo iftop` to view network usage.
        - If not installed, it can be installed via `sudo apt install iftop`
    - Keep an eye on the **peak TX** usage in the bottom left. If it approaches **12.5Gb/s**, then we're reaching the peak threshold of the SKU (Standard_D8ds_v4), and either the VM SKU needs to be increased in size or more VMs need to be added to the region.
```
TX:      cumulative:   5.61GB   peak:   1.62Gb
RX:                    2.42GB            645Mb
TOTAL:                 8.03GB           2.06Gb
```


## Gateway Timeout (502/504)
**Symptom**: Customer indicates that they see HTTP 502 or 504 status codes when retrieving content from packages.microsoft.com.

**Resolution**: Both of these symptoms indicate a "gateway" issue.
Our mirrors serve as reverse caching proxies, and this error indicates:
1. The requested content is not in the local cache
2. The mirror is trying to pull this content into cache, but the origin (Pulp or the nginx proxy wrapped around it) is taking too long to respond.
We already have retries enabled in nginx to prevent this, and the occurrence of this error should be very rare.
- If the error is **transient**, then this should be ignored. These are rare errors that can easily be retried by clients.
- If the error is **persistent** then keep reading.

The central Pulp services are deployed in AKS with auto-scale, so resources should scale up based on demand.
The only remaining piece is the PostgresDB, which does not scale with demand, and may need to be increased.
1. JiT to the AME/Prod subscription (`ae06cb0d-47c5-420b-ac59-8e84bef194bb`).
2. Navigate to the [pmc-prod-pg database](https://ms.portal.azure.com/#@MSAzureCloud.onmicrosoft.com/resource/subscriptions/ae06cb0d-47c5-420b-ac59-8e84bef194bb/resourceGroups/pmcprod/providers/Microsoft.DBforPostgreSQL/flexibleServers/pmc-prod-pg/overview).
3. Scroll down to see the CPU, Memory, and Network utilization.
    - If the CPU or Memory metrics are *consistently* below 100%, and if network usage is *consistently* below 2Gb/s, then the DB is not hitting any limits. Stop troubleshooting here.
    - If the DB is reaching any of the above limits, use the following steps to increase the SKU for this resource.
4. Click the **Compute + Storage** tab on in the left panel.
5. Under Compute Size, choose a larger SKU.
6. Click Save to persist the changes.


## Slow Delivery Speeds
**Symptom:** Customer indicates that they are experiencing slow speeds downloading content from packages.microsoft.com.

**Resolution:** PMC currently offers no SLA for content download speeds.
- Traffic into/out of China is limited, and this is the source of the majority of "slow download" reports.
This is tracked in [this work item](https://msazure.visualstudio.com/One/_workitems/edit/12982300) and will be addressed with future infrastructure improvements.
- By end of 2023, new delivery infrastructure will be deployed, and we'll be in a better position to define SLAs around delivery.
