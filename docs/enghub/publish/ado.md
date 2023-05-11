# Publishing packages via Azure Devops (ADO)
Azure Devops (ADO) is the most common method for publishing packagesm, as it ties easily into build processes and provides a straight-forward automation framework.

## Prerequisites
Some essential steps should be performed before you proceed with a package publishing/release job.
- Onboard with the PMC API as described [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/onboard).
- Ensure you're able to login to an ADO instance. This varies per org.
- Create a build job for your product.
    - This varies per product and is outside the scope of this document.

---
## Create a Service Principal

This Service Principal will be used to create a Service Connection in the next step.
- Create a Service Principal as described [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal).
- Make note of the **Application ID** of your newly created Service Principal, as you'll need it later.

---
## Create a Service Connection

A Service Connection is ADO's resource for communicating with resources outside of ADO - in this case Azure/Keyvault. It will allow you to retrieve the publishing credentials for your publishing job.
- In ADO, click the gear icon in the lower left
- In the Project Settings page, select "Service Connections"
- In the Service Connections page, click "New Service Connection" on the top right.
- In the New Service Connection panel, select "Azure Resource Manager." Scroll to the bottom and click "Next" (bottom right).
- Select Service Principal (Manual) and click Next
- Fill in the following details
    - Environment: Azure Cloud
    - Subscription ID: The Subscription ID where your KeyVault resides
    - Subscription Name: Name of your subscription
    - Service Principal ID: The Application ID of your Service Principal, per the [previous section](#create-a-service-principal).
    - Credential: Select Certificate
    - Certificate: Paste in your PEM-formatted Certificate
    - Tenant ID: The AAD Tenant where your Service Principal resides
        - Corp/Tux-dev: `72f988bf-86f1-41af-91ab-2d7cd011db47`
        - AME/PMC: `33e01921-4d64-4f8c-a055-5bdaffd5e33d`
    - Service Connection Name: A sensible name for your Service Connection
    - Click Verify and Save

---
## Create a Release Job

A Release job is a straight-forward way to publish your content to packages.microsoft.com.
- In ADO, hover over the Release icon in the left panel, and click Releases from the menu that appears.
- In the Releases page, click "+ New" and then "New Release Pipeline"
- When prompted to select a Template, select Empty Job
- In the top panel, supply a name for your new release job
- In the Artifacts Panel (left), click Add
    - Use the available options to select your build artifacts
    - Optionally, use the Azure Repos or Github sources to add your source code. This will allow you to use create/use publishing scripts from your source repo.
- In the Stages panel (middle/right), click under Stage 1 (# job, # task).
    - Under Agent selection, select Azure Pipelines, then an OS of your choice (i.e. Ubuntu Latest).
    - Next to Agent Job, click the + sign and add the following tasks
        - Azure Kay Vault
        - Bash Script
    - Configure the Azure Key Vault task
        - **Azure Subscription:** Select the Azure Subscription for which you added a Service Connection in the previous step
        - **Key Vault**: Select the KeyVault (within your subscription) where your publishing certificate resides
        - **Secrets filter**: Enter the Certificate name (as presented in KeyVault). The Certificate will now be available in other build steps using the name specified here.
    - Configure the Bash Script task
        - Enter the path to a publishing script (in your source folder, or use the "Inline" option to manually enter commands.)
        - Reference the [PMC CLI documentation](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/pmctool) for command reference.
- Click Pipeline in the top-left panel to return to the main page of your release job.
- Click Save to save all your changes
- Be sure to bookmark (or otherwise document) a link to this job, as jobs can be difficult to find.
- Click Create Release if you wish to test out your new publishing job.

--
## Frequently Asked Questions

### How can I publish to tux-dev (rather than Prod) from ADO?

The tux-ingest environment exists wholly within the Corpnet boundary, and it cannot be reached from outside Corpnet.
The standard ADO pool servers exist outside Corpnet in arbitrary Azure IP space and cannot access Corpnet.
If you try to use the default pool servers in ADO to publish to tux-dev, the DNS name for the API service (tux-ingest.corp.microsoft.com) will not be resolved.
Your job will fail, typically with an error along the lines of "Failed to establish a new connection: [Error -2] Name or service not known".

If you need to publish to tux-dev from ADO, the only solution is to create hosted pool inside Corpnet and use that to run your ADO job.
