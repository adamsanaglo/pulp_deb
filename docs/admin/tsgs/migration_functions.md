# Migration Functions
- The Azure Migration Functions keep repo contents in sync between the old codebase (vcurrent) and the new codebase (vnext)
- For an in-depth overview of the Azure Migration Functions, see the [README](https://msazure.visualstudio.com/One/_git/Compute-PMC?path=/migrate/functions/README.md&_a=preview)
- Note that the process_action function will be retried 3 times (you'll see up to 3 invocations when querying below) so a single failure is not necessarily a problem

## Troubleshooting Azure Migration Function issues
- If a migration message fails to process 3 times a Sev 3 IcM issue will be filed that contains the message itself and mentions which environment (prod or tux-dev) the failure is from.
- You can also view failed migration messages from the pmc client with the Repo Admin account.
An easy place to do this in prod is on the pmc-deploy machine. This will list the most recent 10 failures.
    ```bash
    $ pmc repo migration-failures
    ```
- To access the functions for production, you'll need to submit a JiT request for the production subscription 
    - Production sub: `ae06cb0d-47c5-420b-ac59-8e84bef194bb`
- For a high level overview, you can look at the [pmc-prod-migrate app page](https://ms.portal.azure.com/#@MSAzureCloud.onmicrosoft.com/resource/subscriptions/ae06cb0d-47c5-420b-ac59-8e84bef194bb/resourceGroups/pmc-prod-migrate/providers/Microsoft.Web/sites/pmc-prod-migrateapp/functionsList)
    - The Monitor blade for each function shows the 20 most recent invocations and allows you to follow the live logs
        - To see more than the 20 most recent invocations, see the azure insights requests query below
    - [process_action function page](https://ms.portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade/~/functionOverview/resourceId/%2Fsubscriptions%2Fae06cb0d-47c5-420b-ac59-8e84bef194bb%2FresourceGroups%2Fpmc-prod-migrate%2Fproviders%2FMicrosoft.Web%2Fsites%2Fpmc-prod-migrateapp%2Ffunctions%2Fprocess_action)
    - [queue_action function page](https://ms.portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade/~/monitor/resourceId/%2Fsubscriptions%2Fae06cb0d-47c5-420b-ac59-8e84bef194bb%2FresourceGroups%2Fpmc-prod-migrate%2Fproviders%2FMicrosoft.Web%2Fsites%2Fpmc-prod-migrateapp%2Ffunctions%2Fqueue_action)
- Another place to check is at the [service bus queue](https://ms.portal.azure.com/#@MSAzureCloud.onmicrosoft.com/resource/subscriptions/ae06cb0d-47c5-420b-ac59-8e84bef194bb/resourceGroups/pmc-prod-migrate/providers/Microsoft.ServiceBus/namespaces/pmc-prod-migratebus/queues/pmcmigrate/overview)
    - If messages are being enqueued faster than they can be processed, you'll see things pile up in the pmcmigrate queue.
    - If failures are occurring and the alert_failure function is not running for some reason, then you'll see messages in pmcmigrate.deadletter.
	- In normal operation you'll see failed messages in the pmcmigrate-failures queue, which is the same source that you can query / retry using the pmc repo migration-failures command above.
- Lastly, information can be pulled from the [Azure insights app for pmc-prod-migrateapp](https://ms.portal.azure.com/#@MSAzureCloud.onmicrosoft.com/resource/subscriptions/ae06cb0d-47c5-420b-ac59-8e84bef194bb/resourceGroups/pmc-prod-migrate/providers/microsoft.insights/components/pmc-prod-migrateapp/overview)
	- [Link to alerts blade](https://ms.portal.azure.com/#@MSAzureCloud.onmicrosoft.com/resource/subscriptions/ae06cb0d-47c5-420b-ac59-8e84bef194bb/resourceGroups/pmc-prod-migrate/providers/microsoft.insights/components/pmc-prod-migrateapp/alertsV2)
        - Will show any alerts that got fired
	- [Query: Exceptions for the last 12 hours](https://ms.portal.azure.com#@33e01921-4d64-4f8c-a055-5bdaffd5e33d/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/%2Fsubscriptions%2Fae06cb0d-47c5-420b-ac59-8e84bef194bb%2FresourceGroups%2Fpmc-prod-migrate%2Fproviders%2Fmicrosoft.insights%2Fcomponents%2Fpmc-prod-migrateapp/source/LogsBlade.AnalyticsShareLinkToQuery/q/H4sIAAAAAAAAA0utSE4tKMnMzyvmqlEoz0gtSlUoycxNLS5JzC1QsLNVSEzP1zA0ytAEAIJqiQAoAAAA)
	- [Query: Failed invocations for the last 12 hours](https://ms.portal.azure.com#@33e01921-4d64-4f8c-a055-5bdaffd5e33d/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/%2Fsubscriptions%2Fae06cb0d-47c5-420b-ac59-8e84bef194bb%2FresourceGroups%2Fpmc-prod-migrate%2Fproviders%2Fmicrosoft.insights%2Fcomponents%2Fpmc-prod-migrateapp/source/LogsBlade.AnalyticsShareLinkToQuery/q/H4sIAAAAAAAAA11PPQvCMBDd%252BytClyq46F4XRcjSwVWkhOSwkSQXc4ku4m83NLWKtxzv4x7vAtwSUKTqyXzAK8hYsTxR28wK61cj1Kps9BBE1Oj6TlgoHCUpgaiAAJRM3KGaRJWK%252F%252F%252BcT4HSYFL9EQ18A7W7oxxtXLUyUUS7z3UcZYZODf%252BRm3Pu%252FRggwKcGa1%252BsPghDUM%252FS%252FAzbMnHBxXozLN8Ace5%252F%252BAAAAA%253D%253D)
	- Once you have an operation_Id, you can get the invocation logs:
        ```
        traces | where operation_Id =~ 'xxx' | order by timestamp asc
        ```
- When you believe you have resolved the problem causing the messages to fail, you can re-run the failed messages. This will schedule 10 messages at a time for reprocessing, so if there are more failures then that you may have to execute multiple times. 
    ```bash
    $ pmc repo migration-failures --retry
    ```

## Tux-dev Links
No JiT request required. Follow the same process above using the following links.

- [pmc-tux-migrateapp](https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource/subscriptions/e4b53a57-a6fe-4389-8eb2-64a14bef28bd/resourceGroups/pmc-tux-migrate/providers/Microsoft.Web/sites/pmc-tux-migrateapp/appServices)
    - [queue_action function](https://ms.portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade/~/functionOverview/resourceId/%2Fsubscriptions%2Fe4b53a57-a6fe-4389-8eb2-64a14bef28bd%2FresourceGroups%2Fpmc-tux-migrate%2Fproviders%2FMicrosoft.Web%2Fsites%2Fpmc-tux-migrateapp%2Ffunctions%2Fqueue_action)
	- [process_action function](https://ms.portal.azure.com/#view/WebsitesExtension/FunctionMenuBlade/~/functionOverview/resourceId/%2Fsubscriptions%2Fe4b53a57-a6fe-4389-8eb2-64a14bef28bd%2FresourceGroups%2Fpmc-tux-migrate%2Fproviders%2FMicrosoft.Web%2Fsites%2Fpmc-tux-migrateapp%2Ffunctions%2Fprocess_action)
	- Note: the logs don't show up because the functions run in a NSG which the portal can't connect to
- [Service bus queue](https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource/subscriptions/e4b53a57-a6fe-4389-8eb2-64a14bef28bd/resourceGroups/pmc-tux-migrate/providers/Microsoft.ServiceBus/namespaces/pmc-tux-migratebus/queues/pmcmigrate/overview)
- Azure insights app
	- [Alerts](https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource/subscriptions/e4b53a57-a6fe-4389-8eb2-64a14bef28bd/resourceGroups/pmc-tux-migrate/providers/microsoft.insights/components/pmc-tux-migrateapp/alertsV2)
	- [Query: Exceptions for last 12 hours](https://ms.portal.azure.com#@72f988bf-86f1-41af-91ab-2d7cd011db47/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/%2Fsubscriptions%2Fe4b53a57-a6fe-4389-8eb2-64a14bef28bd%2FresourceGroups%2Fpmc-tux-migrate%2Fproviders%2Fmicrosoft.insights%2Fcomponents%2Fpmc-tux-migrateapp/source/LogsBlade.AnalyticsShareLinkToQuery/q/H4sIAAAAAAAAA0utSE4tKMnMzyvmqlEoz0gtSlUoycxNLS5JzC1QsFNITM%252FXMDTK0AQAwMQwNScAAAA%253D)
    - [Query: Failed invocations for last 12 hours](https://ms.portal.azure.com#@72f988bf-86f1-41af-91ab-2d7cd011db47/blade/Microsoft_OperationsManagementSuite_Workspace/Logs.ReactView/resourceId/%2Fsubscriptions%2Fe4b53a57-a6fe-4389-8eb2-64a14bef28bd%2FresourceGroups%2Fpmc-tux-migrate%2Fproviders%2Fmicrosoft.insights%2Fcomponents%2Fpmc-tux-migrateapp/source/LogsBlade.AnalyticsShareLinkToQuery/q/H4sIAAAAAAAAAytKLSxNLS4p5qpRKM9ILUpVKC5NTk4tLlawrVNQckvMKU5VgkuVZOYClSbmFijYKSSm52sYGmVoAgDElMV6QAAAAA%253D%253D)