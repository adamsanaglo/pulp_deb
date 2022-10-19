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
