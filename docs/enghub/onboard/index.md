# Onboarding to PMC

In order to publish content via PMC, you will need to perform some prerequisite tasks (typically one time only per team), then request access to publish to one or more repositories.

- [Pre-prerequisites](#pre-prerequisites)
- [Prerequisites](#prerequisites)
  - [Generate a Certificate](#generate-a-certificate-for-authentication)
  - [Create a Service Principal](#create-the-service-principal)
  - [Configure Service Principal Credentials](#configure-service-principal-credentials)
  - [Create an IcM Queue](#create-an-icm-incident-queue)
  - [Request access to ESRP Signing](#request-access-to-esrp-signing)
- [Requesting Publishing Access](#request-publishing-access)
  - [Request access to existing repos](#request-access-to-existing-reposs)
  - [Request new dedicated repositories](#request-new-dedicated-repositories)

## Pre-prerequisites

Prior to starting this process, you will need the following
- A trusted, OneCert-compatible certificate store. This can be either:
    - [dSMS](https://aka.ms/dsms)
    - An Azure Subcription with KeyVault
- For production (packages.microsoft.com), an AME account and SAW are required *for some onboarding steps*
    - The SAW is *not* required for routine publishing operations. Only to configure the Service Principal and Certificate.
    - Steps for obtaining an AME account and Yubikey can be found [here](https://dev.azure.com/msazure/AzureWiki/_wiki/wikis/AzureWiki.wiki/29758/Account-Creation-and-YubiKeys?anchor=request-a-*me-account).
    - A SAW can be requested from your team admin.
    - AME/SAW are *not* required for tux-dev onboarding/operations

---

## Prerequisites

There are some prerequisite tasks that must be performed before your team can be on-boarded; these tasks create entities or obtain artifacts that are used throughout the operation of the publishing and content delivery infrastructure.

### Generate a certificate for authentication

**Note**: These steps must be performed on a **SAW**. OneCert is *only* available via SAW.

Access to the PMC publishing service is secured via client-side certificate associated with an AAD Service Principal.
You must generate a certificate to be used by your publishing workflow when it uses the PMC CLI.
The recommended way to generate a certificate, per Azure Policy, is [OneCert](https://aka.ms/onecert).
This will result in an auto-rotating certificate, which will save you time in the long-term.

#### *Select a Domain Name for Client Authentication*
In this section you will choose a **domain name** for your authentication certificate.
The domain name *should* be chosen to collect authentication certificates in buckets tied to their purpose.
For example, a team might have multiple pipelines to build and publish packages.
That team might choose `*.pmcclient.prod.ourteam` as the domain for certs that authenticate Service Principals which publish packages to the Prod environment of packages.microsoft.com, and `*.pmcclient.internal.ourteam` for publishing to the Tux-Dev environment. It ultimately doesn't matter what name is used here, as long as it's uniquely associated with your team and, in some way, reflects your team/product name.

The domain doesn't need to *exist*, (no CNAME or DNS registration).
The domain name will not be exported and should not end in .net, .com, etc.
Please don't use *packages.microsoft.com*, it is already in use :)

#### *Register with OneCert*
1. In OneCert, register a domain for the client authentication certificate as documented [here](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/onecert/docs/registering-a-domain-in-onecert) ([Example](OneCert.png))
    1. **Domain Name**: Select a name that's uniquely associated with your team.
        - See the paragraph above if you don't know what name to use here.
    1. **Issuer (v2)**: Select **Private Issuer** -> **AME**
        - Leave *Public Issuer* blank
    1. **Service Tree ID**: Enter your ID from [Service Tree](https://servicetree.msftcloudes.com/#/)
        - You should have used this already when [creating the IcM incident queue](#creating-an-icm-incident-queue).
    1. **Cloud Settings**: This section defines which subscriptions will be allowed to generate the cert. Once configured, any KeyVaults within these subscriptions will be able to generate this cert.
        - Select **Public** (our API exists in Public Azure).
        - Enter the **ID(s) of one or more Azure subscriptions** *that you own* where you want the cert to be generated/reside.
    1. **Owners**: Specify one or more Owners (who can modify this registration in the future)
        - Be sure to set at least one other owner, as team members tend to change over time.

#### *Generate Certificate in KeyVault*
2. Generate a new Certificate in KeyVault, using the Subject/Domain name from the steps above. Reference the [OneCert documentation](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/onecert/docs/requesting-a-onecert-certificate-with-keyvault) and [this example](keyvault.png).
    
    1. **Method of Generation**: Generate
    1. **Certificate Name**: This is up to you.
    1. **Type of Certificate Authority (CA)**: Certificate issued by an integrated CA
    1. **Certificate Authority (CA)**: OneCertV2-Private CA
        - You may have to add this CA if it's the first time you've used it.\
        Follow the steps in the Portal, it's fairly simple.
    1. **Subject**: Use the domain name you registered in OneCert.
        - This should begin with `CN=`, i.e. `CN=pmcclient.prod.ourteam`
    1. **Validity Period**: 12 months
    1. **Content-Type**: PEM (pmc cli is currently incompatible with PFX/PKCS12 certs).
    1. **Lifetime Action Type**: Automatically Renew at a **given number of days before expiry**
    1. **Number of Days Before Expiry**: 275 (Renews every 90 days)




### Create the Service Principal

**Note**: For production/AME Service Principals, these steps must be performed on a **SAW**.

The onboarding/migration process requires you to setup a Service Principal in Azure Active Directory and provide the Application ID associated with that Service Principal. You will then use that Service Principal to authenticate with the PMC API for all publishing actions.

- Follow [these instructions](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal) to create a Service Principal (AKA Application Registration). You must create the Service Principal in the AAD Tenant which matches where you intend to publish content
    - Tux-Dev: Corp/MSIT (`72f988bf-86f1-41af-91ab-2d7cd011db47`)
    - Prod/packages.microsoft.com: AME (`33e01921-4d64-4f8c-a055-5bdaffd5e33d`)

In the main page for your Service Principal you will see an **Application ID** and **Object ID**. Take note of these for subsequent steps.

### Configure Service Principal Credentials

**Note**: For production/AME accounts, these steps must be performed on a **SAW**.

This is the magic step that enables auto-rotation. Once completed, any cert issued by the AME Root CA that matches your subject name will be a valid credential for your account. See [documentation](https://aadwiki.windows-int.net/index.php?title=Subject_Name_and_Issuer_Authentication).
- Download SNIssuerConfig.exe from one of the various sources described [here](https://aadwiki.windows-int.net/index.php?title=Subject_Name_and_Issuer_Authentication#Location_of_signed_version_of_SNIssuerConfig_tool_and_configuration_for_sovereign_clouds)
    - `\\reddog\Builds\branches\git_ests_main_master_latest\release-x64\Product\Binaries\Tools\SNIssuerConfig`
    - Software Center (SAW Only)
- Run `SNIssuerConfig.exe addAppKey <TenantID> <applicationObjectID> AME <subjectName>`
    - `TenantID` is the Tenant in which your Service Principal was created (see [previous section](#creating-the-service-principal))
    - `applicationObjectID` is the **Object ID** from [the previous section](#creating-the-service-principal)
    - `subjectName` is the domain/subject name you registered in the [first section](#generate-a-certificate-for-authentication)
        - **Do not** include the `CN=` prefix here. Just supply the domain/subject name.
- Optionally, run `SNIssuerConfig.exe getProperty <TenantID> <applicationObjectID>` to confirm the change has taken effect.

### Create an IcM incident queue

If a customer contacts CSS with an issue related to a package, an incident may be incorrectly opened against the PMC service itself; we need an IcM queue monitored by your team to which such incidents can be transferred.
The PMC team is responsible only for the health of the publishing and content service infrastructure; we cannot handle issues arising from the content of a package.

Follow the instructions on the [Service Tree hub](https://servicetree.msftcloudes.com/main.html#/) to setup your service and team.
That should create a basic set of IcM queues for your service. You can further manage those queues via the [IcM site](https://aka.ms/icm).

### Request access to ESRP signing

Packages uploaded to packages.microsoft.com must be signed. This provides assurance to our customers that the content is authentic and has undergone some level of validation.
1. Open the [ESRP](https://portal.esrp.microsoft.com/Onboarding/WelcomeCustomer) page.
1. Click Add New Client.
1. Enter the Application ID for the security principal you created for publishing your content.
1. Enter a sensible client name.
1. Select "Sign".
1. Enter one or more Account Owners to be associated with the ESRP account you're creating.
1. Click Save.
1. Click the CodeSign tab.
1. Under Available KeyCodes, select CP-450779-Pgp (note: ESRP keycodes are case sensitive).
1. Click the > button to add it.
1. Click "Request Approval." ESRP will handle it from there.

---

## Request Publishing Access

The full list of existing repositories can be viewed by directly examining the packages.microsoft.com website. Two package/repo formats are currently supported.

- apt (Debian-style "deb") repos: <http://packages.microsoft.com/repos/>
- yum (RHEL-style "rpm") repos: <http://packages.microsoft.com/yumrepos/>

Within each of the above categories, there are two *types* of repositories.
- **"Shared"** repositories, which serve as a "one-stop shop" for customers to get any software for their distro (i.e. Debian 11 or RHEL 9).
    - The repo for a new release of a distro is generally created during the final beta testing phase of the release.
- **"Dedicated"** repositories, which contain content for a specific product.
    - These are typically used if the published packages may conflict with or break user scenarios. Users must "opt in" to the potentially breaking behavior by enabling this repository.

### Request access to existing repos

To request acces to existing "shared" repositories, please fill out [this form](https://msazure.visualstudio.com/One/_workitems/create/Task?templateId=24b8ee70-dc97-4a65-a9fd-66b5eed09b46&ownerId=8480097b-b099-4252-b2e6-6f63a0d143b3).

- The name of your new (or existing) account. Most teams go with the team name or a common abbreviation thereof. For example, dotnet, pas, or iot-edge.
- The IcM queue to which incidents related to the packages you publish can be directed.
- The environment(s) that will you host your packages. PMC supports two publishing and delivery environments: "tux-dev" (accessible only from corpnet) and Prod.
- The aliases of your team's repo admins. Your team's repo admins are the ones who will upload packages to and delete packages from the repositories. At least two aliases are required, in case one admin is unavailable during any active issues. These aliases will be added to the msrepo mailing list, which we use for making announcements about planned outages or new features.
- The Application ID of a service principal that will be used to authenticate requests to our API. See prerequisites, above.

### Request new dedicated repositories

The creation of a dedicated repository is an exception to our recommended practice and requires an elevated bar of approval.
Please submit your request via [this form](https://forms.office.com/pages/responsepage.aspx?id=v4j5cvGGr0GRqy180BHbR0Y-CJ76f3hPsEnpT23ehPxUQjNMN0tJNU9STDI0MlcwOFBSVVU5NlBDNy4u).
Please include this information in your request:

- Business Case for New Repository Exception. Provide an explanation for why access to the existing production repos is insufficient for your team's scenario.
- Desired Name of the New Repository.
- Type of Repository, either "yum" or "apt".
- Distro/Version of the new Repository. For "apt" repos, this names the specific distribution of the repository (stable, disco, xenial, jessie, etc.) you want to create. For more information on this, please contact us.


# Creating a certficate with OpenSSL

*This method is not recommended, and included only for reference.*
Start by generating self-signed certificates holding public and private keys.

```bash
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
Location Name (2 letter code) [AU]:US
State or Province Name (full name) [Some-State]:WA
Locality Name (eg, city) []:Redmond
Organization Name (eg, company) [Internet Widgits Pty Ltd]:Microsoft
Organizational Unit Name (eg, section) []:Azure
Common Name (e.g. server FQDN or YOUR name) []:RepoClient
Email Address []:
```

Append the public key cert to the private key file you just generated (`private.pem`). This extended private key file will be used by the publishing tool, and you'll need to supply it in any scripts that use that tool.

```bash
cat public.crt >> private.pem
```

Associate the .crt file with your Service Principal, via `az cli` or Azure Portal.
