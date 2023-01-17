# Frequently Asked Questions

## Authorization and Access

### The "owners" of our team's security principal have left the company - now what?

You must create a new security principal to be swapped in place of the old.

- Create a new security principal in the correct domain (Corp/MSIT for tuxdev, AME for Prod).
- Open a service request with PMC providing the old GUID you no longer control and the new GUID you'd like to replace it with.
- Open a service request with ESRP to request signing permissions for the new GUID. (Packages signed by the previous GUID remain valid, so there's no need to revoke anything related to it.)
- Update your package production and signing pipeline with the new GUID. 

### Why can't we use a Corp AAD (REDMOND, etc) security principal?

In order to make good on our promise to customers to protect their supply chain, Microsoft has to be very careful to ensure attackers cannot publish packages under "our" name.
Good security practice, and past history, requires an assumption that attackers always have some level of persistent presence within our older (i.e. corporate) domains.
The greater security layered in and around the AME forest provides the higher level of assurance required by our promise to our customers.

## Managing Repositories

### What are shared repositories?

Most repositories are shared by multiple publishers, all of whom can add packages to or remove them from the repo.

### If I publish a package to a shared repository, can anyone else publish a new version of that package, or delete it?

No. We track the security principal which was the first to upload a package to a repo, and we block any attempt to operate on packages with that name in that repo by any other security principal.

### Can I create a repository only I can publish to?

PMC does support dedicated repositories which only one publisher controls, but we're going to ask pointed questions about your business justification, how many packages you intend to publish, and how much complexity you are willing to force your customers to put up with. In general, shared respositories are better for everyone.

### Can I create a repository visible to airgapped clouds?

No. Replication of packages into airgapped clouds is handled by the Repo Depot service.

### How can sovereign clouds access packages published via PMC?

Sovereign clouds can still access the public internet, so packages published to PMC are fully visible from those environments.
Data privacy rules as they apply to various sovereign clouds (e.g. GDPR) are observed across PMC. No data subject to such rules ever leaves the region in which the data was collected.

## Restricting Access to Packages

PMC does not currently support repositories which provide a publisher any control over access to published packages, other than the "corpnet only" restriction provided by tuxdev repos.

### Can I create and publish to a repository that isn't visible under packages.microsoft.com?

### Can I publish to a repository only visible on corpnet?

Yes; that's what the "tuxdev" environment provides.

### Can I publish to a repository only visible to my ADO CI/CD pipeline?

Not at this time. This is a subset of the more general "can I restrict access to packages or repos" question, above.

## Packages Built With OSS Components

There are two cases where PMC packages might use open source:

1. A simple repackage of an upstream OSS project (with our without Microsoft modifications).
1. Use of an open source component as part of a closed-source Microsoft package.

CELA has different license requirements for each; those requirements depend on whether you're building an rpm or deb package.

### What requirements apply when I package an upstream open source codebase into an rpm?

Following community convention, when Microsoft repackages an upstream open source codebase the source to rebuild the package (including Microsoft's modifications) must be made available.
If you have made modifications to the upstream source code you believe cannot be shared, contact [OSS CELA](mailto:OSSStandardsLegal@service.microsoft.com).

1. Build and publish (via PMC) an "srpm" (source rpm) package at the same time you build and publish the matching rpm package.
1. Ensure that the package [SPEC file](https://rpm-packaging-guide.github.io/#what-is-a-spec-file) contains the short form of the license for the source code.
1. Ensure that a copy of the source code license is present in the LICENSE file following [rpm packaging conventions](https://rpm-packaging-guide.github.io/#preparing-source-code-for-packaging).
1. Make sure some human-readable file in your rpm tells the reader how to acquire the corresponding srpm. You can install that file under `/usr/share/doc/_packagename_/` if your package doesn't otherwise create a folder which could be used for this purpose.
1. If the source of your package is maintained in a publicly visible location (e.g. public github repo), the same human-readable document mentioned above (which points to your srpm) should also point to that location (your github repo).

### What requirements apply when I package an upstream open source codebase into a deb?

Following community convention, when Microsoft repackages an upstream open source codebase the source to rebuild the package (including Microsoft's modifications) must be made available.
If you have made modifications to the upstream source code you believe cannot be shared, contact [OSS CELA](mailto:OSSStandardsLegal@service.microsoft.com).

The PMC publishing tools do not yet support building or publishing a "source deb" package.
We expect to deliver this capability in the first quarter of CY2023.

1. Build the source package (source deb) at the same time you build and publish the matching deb package. Make the source deb file visible on the internet, using an Azure storage account or some other mechanism for hosting static content.
1. Ensure that the `debian/copyright` file in your package metadata contains the short form of the license for the source code (see [section 5.9 of the debmake documentation](https://www.debian.org/doc/manuals/debmake-doc/ch05.en.html#copyright)).
1. Ensure that a copy of the source code license is present following [Debian packaging policy](https://www.debian.org/doc/debian-policy/ch-source.html).
1. Your binary package must install a human-readable file in `/usr/share/doc/_packagename_/` which tells the reader how to acquire the corresponding source deb package. Work with your CELA contact to develop the text.
1. If the source of your package is maintained in a public github repo, the same human-readable document mentioned above (which points to your source deb package) should also point to your github repo.
1. Once support for "source deb" packages is added to PMC, publish your source deb package and revise the file(s) in your deb package with updated information about how to install the source deb.

### What requirements apply when I use open source components in closed-source Microsoft packages?

A closed-source Microsoft binary published on PMC will often include or depend on open source components. Take the following steps to ensure license compliance in these instances.

1. Follow the standard Microsoft process to [register all dependences of your package](https://docs.opensource.microsoft.com/using/guidance-for-open-source-usage/registering-open-source-usage/) (including dependences on other deb or rpm packages) in component governance.
1. Resolve all of your legal alerts in [Component Governance](https://docs.opensource.microsoft.com/tools/cg/).
1. In resolving legal alerts, work with OSS CELA to determine whether the code you use requires you to provide any source code and how you should provide that source.
1. Use Component Governance to generate a [NOTICE file](https://docs.opensource.microsoft.com/using/guidance-for-open-source-usage/required-notice-template/) for your Microsoft package.
1. Your package must install that notice file as `/usr/share/doc/_packagename_/NOTICE`.
1. Ensure that your package has the relevant End User License Agreement for the closed-source Microsoft packages in the standard metadata location for your package type.
    - For **rpm** packages, that standard location is the [SPEC file](https://rpm-packaging-guide.github.io/#what-is-a-spec-file).
    - For **deb** packages, that standard location is the `debian/copyright` file.
