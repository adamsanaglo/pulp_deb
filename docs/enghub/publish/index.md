# Publishing a package to packages.microsoft.com (PMC)
This guide explains how to publish packages to packages.microsoft.com (PMC). Currently, only deb and rpm packages are supported.

- [Onboarding](#onboarding)
- [Client Configuration](#client-configuration)
- [Sign the Package](#sign-the-package)
- [Publish the Package](#publishing-the-package)
    - [Upload the package](#upload-the-package)
    - [Add the uploaded package(s) to a repository](#add-uploaded-packages-to-a-repository)
    - [Publish the Repository](#publish-the-repository)

## Onboarding
Before uploading to packages.microsoft.com (or related offerings such as tux-dev), you must onboard as documented [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/onboard).

## Client Configuration
Once you've onboarded your account, you will need the publishing CLI and a valid configuration.
- The CLI can be installed as described [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/pmctool#installing-the-pmc-client).
- You will then need a configuration file, as described [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/pmctool#configuration-file)
    - This configuration format supports multiple profiles, which gives you flexibility if you have multiple publishing accounts. See the link above for details.
    - Most of the publishing options can also be overridden using command-line options. This is useful if you want to alter your publishing behavior without modifying your configuration file.

## Sign the Package
Packages must be signed prior to upload, otherwise they'll be rejected.
- During onboarding, you should have performed the steps [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/onboard#request-access-to-esrp-signing) to request access to the appropriate signing key.
- The final step of your build process should use ESRP to sign your deb/rpm.
    - The ESRP docs [here](https://microsoft.sharepoint.com/teams/prss/esrp/info/SitePages/Linux%20GPG%20Signing.aspx) explain that process.
    - The most straight-forward method is to use the [ESRP Codesign Task for ADO](https://microsoft.sharepoint.com/teams/prss/esrp/info/ESRP%20Onboarding%20Wiki/Integrate%20the%20ESRP%20CodeSign%20Task%20into%20ADO.aspx). This will require a signing configuration, which is included here for convenience.
```json
[
    {
        "KeyCode" : "CP-450779-Pgp",
        "OperationCode" : "LinuxSign",
        "Parameters" : {},
        "ToolName" : "sign",
        "ToolVersion" : "1.0"
    }
]
```
## Publishing the Package
This section summarizes the steps for publishing to a repo. More details on the pmc cli can be found [here](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/pmctool) or by running `pmc --help`.

### Upload the package
The first step in publishing is to upload the package.

```bash
# Upload a single file
$ pmc package upload $FILE

# This operation also supports batch uploading an entire directory of packages
$ pmc package upload $DIRECTORY

# Optionally, use the --id-only option, which returns just the package ID(s)
$ pmc --id-only package upload $FILE
```

### Add uploaded package(s) to a repository
The next step is to associate the package(s) with a repository. Internally, each package is stored exactly once, but can be associated with multiple repos. Multiple packages can be specified in a single operation, but only a single repo can be specified at once.

**Note** the following commands accept either the repo **name** or the repo **id**. However, note that the repo name will have a suffix indicating the *type* of repo. This is to differentiate apt and yum repos with overlapping names.
- `azurecore-apt` Is the [*apt/deb* repo named azurecore](https://packages.microsoft.com/repos/azurecore/).
- `azurecore-yum` Is the [*yum/rpm* repo for azurecore](https://packages.microsoft.com/yumrepos/azurecore/).

```bash
# This step uses the ID(s) of the package(s) uploaded in the previous step
$ pmc repo package update --add-packages $PKG_ID $REPO_NAME

# Specify more than one package by separating the ID's with a semi-colon
$ pmc repo package update --add-packages $PKG_ID1,$PKG_ID2 $REPO_NAME

# For apt repos, you must specify the "release" into which the package will be published
$ pmc repo package update --add-packages $PKG_ID $REPO_NAME $RELEASE
```

### Publish the Repository
In order for the changes to take effect, the repo must be published. This will cause metadata to be generated and signed. The new content will then be made available publicly.

```bash
$ pmc repo publish $REPO_NAME
```
