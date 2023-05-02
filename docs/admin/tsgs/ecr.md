# Emergency Certificate Rotation (ECR)
- [Background](#background)
- [Certificate Inventory](#certificate-inventory)
    - [AME Certs](#amepmc-prod-ae06cb0d-47c5-420b-ac59-8e84bef194bb)
    - [Corp Certs](#corpazure-linux-apt-repo-d7015505-773d-4c07-bbba-2ddf41b33414)
- [ECR Drill Preparation](#ecr-drill-preparation)
- [Issue New Certificates](#issue-new-certificates)
- [Deploy Certs to AME Subscription](#deploy-certs-to-ame-subscription)
    - [Update AKS Deployment](#update-aks-deployment)
    - [Update Migration Function](#update-migration-function)
- [Deploy Certs to Corp Subscription](#deploy-certs-to-corp-subscription)
    - [Update API Server](#update-api-server)
    - [Deploy Mirror TLS Cert](#deploy-mirror-tls-cert)
    - [Deploy GCS Cert](#deploy-gcs-cert)
- [End ECR Drill](#end-ecr-drill)

## Background
Azure policy requires each service to be capable of rotating all production certs within a 24-hour window.
Further, this capability must be exercised once every 6 months.
This is to ensure that, if a certificate or issuer is compromised, new certs can be deployed to remediate security impact.
Further detail can be found in the [ECR self-serve guidance](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/autorotationandecr/ecrdrillselfserve).

NOTE: Some of the steps in this guide refer to the Corp subscription, which is where our legacy API resides.
This subscription is slated for deprecation in late 2023.
So the Corp subscription may not be in scope for rotation, depending on when the ECR occurs, and which certificates are in scope at that time.

## Certificate Inventory
This section captures an inventory of all certs and how they're used.
Many of these certs are used for client auth with Subject Name Issuer (SNI) authentication.
Once they're rotated, no further action is required.
The tables below include a Deploy column, which describes how each cert is rolled out to prod.
- Auto: Latest secret is fetched/used whenever necessary
- Routine: Deployed whenever an AKS or AzureFunction deployment occurs
- ClientAuth: Used strictly for client authentication
    - Mostly used in ADO jobs, which fetch the latest secret whenever a job is run
    - May need to manually download for *interactive* scenarios
- Manual: Requires manual steps to deploy

### AME/PMC Prod (ae06cb0d-47c5-420b-ac59-8e84bef194bb)
|KeyVault|Cert Name|Purpose|Impact|Deploy|
|--------|---------|-------|------|------|
|pmcprod|accountAdmin|Admin Account|No impact (SNI)|ClientAuth|
|pmcprod|deploy|AAD Deploy Account|No Impact (SNI)|ClientAuth|
|pmcprod|esrp-auth-prod|ESRP Authentication|No Impact (SNI)|Routine|
|pmcprod|esrp-sign-prod|ESRP Request Signing|No Impact (SNI)|Auto|
|pmcprod|migrationAccount|Service-to-Service Auth|No Impact (SNI)|Routine|
|pmcprod|packageAdmin|Admin Account|No Impact (SNI)|ClientAuth|
|pmcprod|pmcDistroTLS|TLS|No Impact (TLS)|Routine|
|pmcprod|pmcIngestTLS|TLS|No Impact (TLS)|Routine|
|pmcprod|repoAdmin|Admin Account|No Impact (SNI)|ClientAuth|

### Corp/Azure Linux Apt Repo (d7015505-773d-4c07-bbba-2ddf41b33414)
|KeyVault|Cert Name|Purpose|Impact|Deploy|
|--------|---------|-------|------|------|
|apt-repo|apt-api-ssl|API TLS Cert|No impact (TLS)|Manual|
|apt-repo|apt-gcs|GCS|No Impact Expected|Manual|
|apt-repo|apt-ssl-euap|EUAP TLS Cert|No Impact (TLS)|Manual|
|apt-repo|apt-ssl-new|Mirror TLS Cert|No Impact (TLS)|Manual|
|apt-repo|esrp-auth|ESRP Authentication|No Impact (SNI)|Auto|
|apt-repo|esrp-codesign|ESRP Request Signing|No Impact (SNI)|Auto|
|apt-repo|repoadmin|Admin Account|No Impact (SNI)|ClientAuth|
|apt-linux-geneva|geneva|MDSD/GCS Auth|No Impact Expected|Manual|

## ECR Drill Preparation
**For real-world events (rotating certs due to legitimate compromise) skip this section.**
- Review the prerequisites documented in the [ECR self-serve guidance](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/autorotationandecr/ecrdrillselfserve#pre-requisites--drill-preparation).
- Generate an IcM using the provided [IcM Template](https://portal.microsofticm.com/imp/v3/incidents/create?tmpl=03A1UH) as documented in the [ECR self-serve guidance](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/autorotationandecr/ecrdrillselfserve#drill-execution).
- Note that as certs are deployed, you will need to gather "evidence" (AKA screenshots/logs/etc) reflecting that the newly generated certs are actually in use.

## Issue New Certificates
In this section we generate new certificates in KeyVault.

## Issue new AME Certificates
- SSH to the pmc-deploy VM
- [Sync the compute-pmc repo](#clone-the-compute-pmc-repo) (if not already present)
- Navigate to the `tools` folder
- Run the `ecrtool.py` script as shown below. This will generate new versions of each pertinent certificate.
    ```bash
    $  ./ecrtool.py -r ecr/prod-ame.json
    ```
- NOTE: This uses the VM's MSI for authentication.
If any issues occur, ensure the jumpbox has access to access to Get, List, and Create Certificates.

### Issue new Corp Certificates
- SSH to the "sark-apt-wus" jumpbox
- [Sync the compute-pmc repo](#clone-the-compute-pmc-repo) (if not already present)
- Navigate to the `tools` folder
- Run the `ecrtool.py` script as shown below.
This will generate new versions of each pertinent certificate.
    ```bash
    $ for file in ecr/prod-corp-*.json; do ./ecrtool.py -r $file; done
    ```
- NOTE: This uses the VM's MSI for authentication.
If any issues occur, ensure the jumpbox has access to access to Get, List, and Create Certificates.
- NOTE: Multiple files are in use here because certs have different scopes.
    - `prod-corp-api.json`: Downloaded only to API server
    - `prod-corp-mirrors.json`: Downloaded only to jumpbox/mirrors
    - `prod-corp-geneva.json`: Downloaded to all servers
    - `prod-corp-rotateonly.json`: Not downloaded to any server

## Deploy Certs to AME Subscription
This section covers deploying newly rotated certificates pertinent to the AME subscription.
As mentioned previously, many certs use SNI, so no further action is required.
This section covers certificates for which some additional action is necessary.

### Update AKS deployment
- SSH to the pmc-deploy server.
- Update the AKS containers using the existing [API deployment TSG](https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/_layouts/OneNote.aspx?id=%2Fteams%2FLinuxRepoAdmins%2FShared%20Documents%2FGeneral%2FLinux%20Repo%20Admins&wd=target%28Main.one%7CEEBC32ED-2430-4988-8FE0-096D42FC44C1%2FAPI%20Code%20Deployment%7C8C5BAF54-6F08-4E86-B56E-5E14B37505DC%2F%29).
- When complete, the following certs will be rolled out to production.
    - esrp-auth-prod
    - esrp-sign-prod
    - pmcDistroTLS
    - pmcIngestTLS

### Update Migration Function
- Follow [this TSG](https://msazure.visualstudio.com/One/_git/Compute-PMC?path=/migrate/functions) to deploy the Azure Functions, which will pull in the latest certs.
- When complete, the following cert will be rolled out to production.
    - migrationAccount

## Deploy Certs to Corp Subscription
This section covers deploying newly rotated certificates to the "vCurrent" Corp subscription. This includes some manual steps, as this infrastructure is on path to deprecation.

### Update API Server
- SSH to the API server (`azure-apt-cat.cloudapp.net`)
- If not already present, clone the [csd.apt.linux](https://microsoft.visualstudio.com/OSGCXE/_git/csd.apt.linux) repo.
- If not already present, [clone the compute-pmc repo](#clone-the-compute-pmc-repo).
- Navigate to the `Compute-PMC/tools` folder
- Run the following to download the API TLS cert
    ```bash
    ./ecrtool.py -d ecr/prod-corp-api.json
    ```
- Save the download private key to `/etc/azure-aptcatalog/server.key`
- Save the downloaded cert/chain to `/etc/azure-aptcatalog/server.crt`
- Within the csd.apt.linux repo, navigate to the server folder.
- Run the following command to restart all containers
    ```bash
    $ sudo ./run_ansible_playbook.sh azure-aptcatalog aptly createrepo_c start
    ```
- Navigate to the repoclient folder and confirm you're able to reach the API and perform basic commands
    ```bash
    $ cd ../repoapi_client
    $ repoclient repo list
    ```
- When complete, the following certs will be rolled out to production.
    - apt-api-tls
    - esrp-auth (automatically retrieved during restart)
    - esrp-codesign (automatically retrieved during restart)

### Deploy Mirror TLS Cert
- SSH to the `sark-apt-wus` jumpbox
- If not already present, [clone the compute-pmc repo](#clone-the-compute-pmc-repo).
- Navigate to the `Compute-PMC/tools` folder
- Run the following to download the mirror TLS certs
    ```bash
    ./ecrtool.py -d ecr/prod-corp-mirrors.json
    ```
- EUAP mirrors
    - Manually separate the certificate and key into two separate files
        - Cert is downloaded as a single PEM file, but nginx expects two separate files
    - Navigate to the `Compute-PMC/edge` folder
    - Run the `deploy-tls.sh` script to deploy to each EUAP mirror. Example below targets EUAP1
        ```bash
        ./deploy-tls.sh /path/to/cert.crt /path/to/key.key euap1
        ```
    - Navigate to [https://pmc-beta.trafficmanager.net](https://pmc-beta.trafficmanager.net) and confirm no TLS errors are encountered.
- Prod mirrors
    - Manually separate the certificate and key into two separate files
        - Cert is downloaded as a single PEM file, but nginx expects two separate files
    - Navigate to the `Compute-PMC/edge` folder
    - Run the `deploy-tls.sh` script to deploy to each prod mirror. Example below targets wus1
        ```bash
        ./deploy-tls.sh /path/to/cert.crt /path/to/key.key wus1
        ```
    - Navigate to [https://packages.microsoft.com](https://packages.microsoft.com) and confirm no TLS errors are encountered.
- When complete, the following certs will be rolled out to production.
    - apt-ssl-euap
    - apt-ssl-new

### Deploy GCS Cert
1. SSH to the `sark-apt-wus` jumpbox
2. If not already present, [clone the compute-pmc repo](#clone-the-compute-pmc-repo).
3. Navigate to the `Compute-PMC/tools` folder
4. Run the following to download the mirror TLS certs
    ```bash
    ./ecrtool.py -d ecr/prod-corp-geneva.json
    ```
5. Install the private key to `/etc/mdsd.d/gcskey.pem`
6. Install the cert/chain to `/etc/mdsd.d/gcscert.pem`
7. Run `sudo service mdsd restart` to restart mdsd
8. Check `/var/log/mdsd.err` to ensure the cert is accepted.
9. Repeat steps 5-8 on **all mirrors** (using the cert downloaded in step 4)
10. Repeat steps 1-8 on the (`azure-apt-cat.cloudapp.net`).
11. When complete, the following certs will be rolled out to production.
    - geneva

## End ECR Drill
**For real-world events (rotating certs due to legitimate compromise) ignore this section.**
### Collect Evidence
In this section we gather evidence (screenshots/logs) in order to receive "credit" for our ECR drill.
- Browse to each of the following URLs, click the lock icon (top left) and get a screenshot of the certificate info (including validity period and thumbprint)
    - [https://pmc-ingest.trafficmanager.net/api/v4](https://pmc-ingest.trafficmanager.net/api/v4)
    - [https://pmc-distro.trafficmanager.net](https://pmc-distro.trafficmanager.net)
    - [https://azure-apt-cat.cloudapp.net](https://azure-apt-cat.cloudapp.net)
    - [https://packages.microsoft.com](https://packages.microsoft.com)
    - [https://pmc-beta.trafficmanager.net](https://pmc-beta.trafficmanager.net)
### Attach Evidence and Close IcM
This section summarizes steps 5-8 from the [official guidance](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/autorotationandecr/ecrdrillselfserve#drill-execution)
- Attach "evidence" of rotated certs (from prior steps) to the IcM that was created earlier.
- Link to this TSG in the "Diagnostics" section of the IcM.
- Mark the IcM as mitigated.
- If any gaps or issues were identified, file a bug and link it to the "Root Cause" section of the IcM.
- Notify/work with the [Security Champ](https://eng.ms/docs/products/onecert-certificates-key-vault-and-dsms/key-vault-dsms/autorotationandecr/gettinghelp#cai-org-security-champ-listing) to validate and resolve the IcM.


## References
### Clone the csd.apt.linux repo
```bash
git clone https://microsoft.visualstudio.com/OSGCXE/_git/csd.apt.linux
```

### Clone the Compute-PMC repo
```bash
git clone https://msazure.visualstudio.com//One/_git/Compute-PMC
```
