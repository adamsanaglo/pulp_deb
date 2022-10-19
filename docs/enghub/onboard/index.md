# Onboarding to PMC

In order to publish content via PMC, you will need to perform some prerequesite tasks (typically one time only per team), then request access to publish to one or more repositories.

## Prerequisites

There are some prerequisite tasks that must be performed before your team can be on-boarded; these tasks create entities or obtain artifacts that are used throughout the operation of the publishing and content delivery infrastructure.

### Generate a certificate for authentication

Access to the PMC publishing service is secured via client-side certificate associated with aa security principal
Generate a certificate that will be used by this Service Principal for login. There are many ways to generate a certificate.
One of the simplest is via OpenSSL:

```
$ openssl req -x509 -nodes -days 730 -newkey rsa:2048 -keyout private.pem -out public.crt
Generating a 2048 bit RSA private key
............................................................................+++
....................+++
writing new private key to 'private.pem'
-----
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Country Name (2 letter code) [AU]:US
State or Province Name (full name) [Some-State]:WA
Locality Name (eg, city) []:Redmond
Organization Name (eg, company) [Internet Widgits Pty Ltd]:Microsoft
Organizational Unit Name (eg, section) []:Azure
Common Name (e.g. server FQDN or YOUR name) []:RepoClient
Email Address []:
```

Append the public key cert to the private key file you just generated (`private.pem`). This extended private key file will be used by the publishing tool, and you'll need to supply it in any scripts that use that tool.

```
$ cat public.crt >> private.pem
```

### Creating the security principal

All PMC actions must be performed by an authenticated security principal. The API uses Azure AD / OAuth to perform authentication, and the PMC service permits a principal ("account") to perform only the actions authorized for it. New accounts will only be configured with Azure AD; any existing accounts which used previously-supported authentication models will be migrated to this new authentication model. The onboarding/migration process requires you to setup a Service Principal in Azure Active Directory and provide the Application ID associated with that Service Principal.

Follow [these instructions](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal) to create a Service Principal (AKA Application Registration). You must create the Service Principal in the environment which matches the one where you intend to publish content (Corp/MSIT for tuxdev, AME for Prod).

In the main page for your Service Principal you will see an Application ID. This is what you need to provide when requesting access.

Once you've created the service principal, you must associate with it the certificate you created as part of the "Generate a certificate for authentication" prerequisite task.

- In the Azure Portal, navigate to the Service Principal.
- In the top left, click settings.
- In the right panel, click keys.
- In the top panel, click upload public key.
- Browse to the .crt file you previously generated and upload it.
- In the top panel, click save.

### Creating an IcM incident queue

If a customer contacts CSS with an issue related to a package, an incident may be incorrectly opened against the PMC service itself; we need an IcM queue monitored by your team to which such incidents can be transferred.
The PMC team is responsible only for the health of the publishing and content service infrastructure; we cannot handle issues arising from the content of a package.

Follow the instructions on the [Service Tree hub](https://servicetree.msftcloudes.com/main.html#/) to setup your service and team.
That should create a basic set of IcM queues for your service. You can further manage those queues via the [IcM site](https://aka.ms/icm).

### Requesting access to ESRP signing

1.	Open the [ESRP](https://portal.esrp.microsoft.com/Onboarding/WelcomeCustomer) page.
1.	Click Add New Client.
1.	Enter the Application ID for the security principal you created for publishing your content.
1.	Enter a sensible client name.
1.	Select "Sign".
1.	Enter one or more Account Owners to be associated with the ESRP account you're creating.
1.	Click Save.
1.	Click the CodeSign tab.
1.	Under Available KeyCodes, select CP-450779-Pgp (note: ESRP keycodes are case sensitive).
1.	Click the > button to add it.
1.	Click "Request Approval." ESRP will handle it from there.

### Selecting existing repositories


## Requesting Publishing Access

To request publishing access, please fill out [this form](https://msazure.visualstudio.com/One/_workitems/create/Task?templateId=24b8ee70-dc97-4a65-a9fd-66b5eed09b46&ownerId=8480097b-b099-4252-b2e6-6f63a0d143b3).

- The name of your new (or existing) account. Most teams go with the team name or a common abbreviation thereof. For example, dotnet, pas, or iot-edge.
- The IcM queue to which incidents related to the packages you publish can be directed.
- The environment(s) that will you host your packages. PMC supports three publishing and delivery environments: PPE, "tux-dev" (accessible only from corpnet), and Prod.
- The aliases of your team's repo admins. Your team's repo admins are the ones who will upload packages to and delete packages from the repositories. At least two aliases are required, in case one admin is unavailable during any active issues. These aliases will be added to the msrepo mailing list, which we use for making announcements about planned outages or new features.
- The Application ID of a service principal that will be used to authenticate requests to our API. See prerequisites, above.

### Requesting new dedicated repositories

A dedicated repository is one to which only one publisher is granted access. The creation of a dedicated repository is an exception to our recommended practice and requires an elevated bar of approval. Please submit your request via [this form](https://forms.office.com/pages/responsepage.aspx?id=v4j5cvGGr0GRqy180BHbR0Y-CJ76f3hPsEnpT23ehPxUQjNMN0tJNU9STDI0MlcwOFBSVVU5NlBDNy4u). Please include this information in your request:

- Business Case for New Repository Exception. Provide an explanation for why access to the existing production repos is insufficient for your team's scenario.
- Desired Name of the New Repository.
- Type of Repository, either "yum" or "apt".
- Distro/Version of the new Repository. For "apt" repos, this names the specific distribution of the repository (stable, disco, xenial, jessie, etc.) you want to create. For more information on this, please contact us.
