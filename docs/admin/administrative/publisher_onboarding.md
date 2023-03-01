# Publisher Onboarding
- [Background/Context](#backgroundcontext)
- [Prerequisites](#prerequisites)
- [Request Validation](#request-validation)
- [Configure/Enable the Publisher Account](#configureenable-the-publisher-account)
- [Create a New Account](#create-a-new-account)
- [Notification/Documentation](#notificationdocumentation)

## Background/Context
This document explains how to onboard publishers with the vNext API. This focuses on publishers who are already onboarded with vCurrent, but may be used for general onboarding.

Note that his guide refers to multiple types of "ID's". For clarity, the table below explains each type of ID.

|Type|Description|
|----|-----------|
|ApplicationID (AppID)|This is an ID associated with an Application or Service Principal in Azure Active Directory (AAD). The publisher will configure this ID in the `msal_client_id` field of their config.|
|ObjectID (oid)|This is a different type of ID associated with an Application/Service Principal. In some cases, a Service Principal can exist in multiple [tenants](https://learn.microsoft.com/en-us/microsoft-365/education/deploy/intro-azure-active-directory). The Application ID will be differ in each tenant, but the Object ID will stay the same. The Object ID is set in our database for authentication purposes.|
|Account ID (ID)|In our database, each account gets an ID. This is distinct from the OID (above). If a publisher gets a new Service Principal for publishing, we can update their OID in the database, but their account ID stays the same. The account ID is primarily for tracking account permissions. The account *name* may be used during API calls, but the **account ID** is what's stored in the database.|

See below for a brief outline of how each ID is used in a given request.
1. Prior to contacting our API, the publisher first sends an authentication request to AAD. This request uses their **AppID** and Certificate.
2. If authentication is successful, AAD returns a [bearer token](https://swagger.io/docs/specification/authentication/bearer-authentication/) to the requester.
3. The requester then submits their request to the PMC API along with the bearer token.
4. When the PMC API receives this request, the token is validated for authenticity, and if it's valid, the **OID** is parsed from the token (AuthN).
5. The PMC API then queries the database using the **OID** to identify the **Account ID**.
6. The database is then queried using the **Account ID** to determine if the requestor has permission to perform the desired action (AuthZ).
7. Assuming the above steps are successful, the request is then queued for action by a pulp-worker.

## Prerequisites
- A Work Item filed by the publisher with the following details
    - The Account Name
    - The Application ID (AppID) or Object ID (OID) of their new AME publishing account.
    - One or more e-mail addresses (or DL) for the individuals who will "own" this account.
    - The IcM Service and Team for this publisher.
- API Access
    - A PMC Cli environment with Account Admin and Repo Admin permission.
    - **NOTE**: PMC-Deploy is useful for this purpose
    - **NOTE**: Refer to [OneNote](https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/_layouts/OneNote.aspx?id=%2Fteams%2FLinuxRepoAdmins%2FShared%20Documents%2FGeneral%2FLinux%20Repo%20Admins&wd=target%28Main.one%7CEEBC32ED-2430-4988-8FE0-096D42FC44C1%2FGeneral%7C467692A0-4336-4466-9E46-6EC5630F65DB%2F%29) for account details.
- Assign yourself as the owner of the work item, to avoid duplication of effort :)

## Request Validation
- **Confirm this isn't a social-engineering attempt.** Given the account name, look up the old account in [OneNote](https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/_layouts/OneNote.aspx?id=%2Fteams%2FLinuxRepoAdmins%2FShared%20Documents%2FGeneral%2FLinux%20Repo%20Admins&wd=target%28Main.one%7CEEBC32ED-2430-4988-8FE0-096D42FC44C1%2FPMC%20Contacts%7C2069C3A2-3E29-C34F-88E5-872C01A136BD%2F%29) (and/or the Publisher list linked from there). Confirm at least one of the following:
    - That the requestor is one of the previously known contacts.
    - That the requestor is in the same reporting structure as a previously known contact.
    - That a previously known contact is in the e-mail thread (implying tacit approval).
- **Confirm the AppID/OID**. Confirm the Application ID or Object ID given by the customer is valid via one of the following methods.
    - Use the Azure CLI
        - Login to the azure CLI using AME credentials. PMC-Deploy is a sensible place to do this.
        - Run the following command, which will give you the account's OID, given its Application ID.
        ```bash
        az ad sp show --id ${appID} --query objectId --out tsv
        ```
    - Use the Azure Portal
        - Login to the [Azure Portal](https://ms.portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/Overview) with AME credentials and browse to the AAD Panel (linked above)
        - Use the search field  to search for the provided ID.
        - If no results appear, then the ID is invalid. It may be for a different AAD Tenant. Refer the publisher to the [Onboarding Directions](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/onboard) and remind them that the account must be in AME.
        - If the account does appear, click on the result under Enterprise Applications.
        - Take note of the **Object ID** on this page. This is the ID we will need for subsequent steps.
- **Check for existing Account**
    - Login to an environment where you have access to PMC CLI and Account Admin credentials.
    - Run the following command to see if the account exists.
    ```bash
    pmc account show ${NAME}
    ```
    - If it does exist, proceed with the [next section](#configureenable-the-publisher-account)
    - if it does *not* exist, skip to the [subsequent section](#create-a-new-account).


## Configure/Enable the Publisher Account
In this case, an account already exists for this publisher. We'll simply enable it, configure the latest contact information, and ensure repo access has been granted. The following steps require the *ID* or *NAME* of the account in question.
- Run the following command to enable the account with the new OID and details.
```bash
pmc account update --oid ${OID} --icm-service ${ICM_SERVICE} --icm-team ${ICM_TEAM} --contact-email ${CONTACT_EMAIL} --enabled ${ID_OR_NAME}
```
- Run the following command to see if any repo permissions have been granted.
```bash
pmc access repo list --account ${ID_OR_NAME}
```
- If any results are found, then access has been granted and the account is ready for use. Proceed to the [final section](#notificationdocumentation).
- If results are *not* found, then we'll need to correct this.
    - Use [this ADO job](https://microsoft.visualstudio.com/OSGCXE/_release?definitionId=897&view=mine&_a=releases) to list repos in vCurrent, and identify repos to which the publisher previously had access.
    - In vNext, grant permissions for all the associated repos using the following command. This command supports a regex for matching multiple repos.
```bash
pmc access repo grant ${ACCOUNT_NAME} ${REPO_NAME|REGEX}
```
- This step is complete; skip to the [final section](#notificationdocumentation).


## Create a New Account
This step assumes you have a PMC Cli environment and have completed [validation](#request-validation). Since we'll be creating a new account, you may have to review the work item or chat with the requestor to determine to which repositories they need access.
- Run the following command to create the new publishing account.
```bash
pmc account create ${OID} ${NAME} ${CONTACT_EMAIL} ${ICM_SERVICE} ${ICM_TEAM}
```
- Take note of the id (not the OID) of the newly created account
- Grant access to one or more repos, as agreed upon with the requestor, using the following command:
```bash
pmc access repo grant ${ACCOUNT_NAME} ${REPO_NAME|REGEX}
```
- Proceed to the next section.

## Notification/Documentation
At this point, the request is fulfilled.
- Respond to the customer via email, CC'ing aztuxrepo DL, to inform them that their account is ready for use.
- Update and close the work item as follows
    - Prepend the string `[ACCOUNT_NAME]` to the work item's title.
    - Add a `vnext_onboard` tag to the work item.
    - Mark it as "Done" and Save/Close.

