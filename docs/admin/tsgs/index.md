# Common Issues

# Definitions
- **Distribution**: AKA distro. A pulp concept, which defines a url at which the repo will be surfaced to customers.
A single repo can have multiple distros, and at least one distro is needed for a repo to be visible to customers.
Most repos have 1-2 distros.
- **Ingestion**: The process of parsing an uploaded package, which includes generating metadata.
- **Package**: An artifact that customers install to enable new software/libraries.
PMC currently supports deb and rpm package formats.
- **PMC**: Packages.microsoft.com.
This is the distribution endpoint for delivering packages to customers, but is used to refer to the service as a whole.
- **Pulp**: An [open-source project](https://pulpproject.org/) for managing package repositories.
This is the foundation for the modern PMC infrastructure.
- **Release/Pocket/Dist (deb repos)**: A subdivision within deb repos (does not apply to rpm repos).
While all packages in a given repo reside in a single [pool](https://packages.microsoft.com/repos/azurecore/pool/main/), the metadata is divided into one or more [releases/pockets/dists](https://packages.microsoft.com/repos/azurecore/dists/).
These allow a customer opt in to a specific update channel (i.e. unstable vs stable)
- **Release (Pulp)**: Pulp has an additional `Release` concept.
When changes are made to a repository, those changes are not visible to customers until a `Release` is created.
Repos can have multiple `Releases` and Pulp must be told which `Release` to present to customers.
In the `pmc` CLI, this is managed via `pmc repo publish`.
This creates a new `Release` and sets it as  the active `Release` for this repo.
- **Remote**: A pulp concept, which refers to *source* repository from which packages will be synchronized into pulp.
    - The legacy environment currently serves as the remote for most repos.
- **Repository**: A collection of packages and associated metadata.
Customers enlist in repositories, so that packages can be easily installed with common tools (apt-get, yum, tdnf, etc).
- **Repository Metadata**: The plaintext files which describe which packages reside in a repo. Clients use this for package installation and dependency resolution. This is a core part of the contract with our customers.

## Shared/Prod repos
These are individual repos broken out by distro/release (i.e. Ubuntu 18.04, RHEL 9.0, etc).
They serve as a "one stop shop" for users of a given distro/release to consume all MSFT packages (az cli, powershell, dotnet, etc).
These repos are easily identifiable because their repo name matches [^microsoft-.*-prod].

These repos have two "distributions", for example:
- `/repos/microsoft-ubuntu-bionic-prod`
- `/ubuntu/18.04/prod`

These repos have additional artifacts to simplify customer onboarding:
- A bootstrap config file (i.e. `/config/ubuntu/18.04/prod.list`)
- A bootstrap config package (i.e. `/config/ubuntu/18.04/packages-microsoft-prod.deb`)

Shared/Prod repos also have multiple update channels (i.e. insiders-fast, insiders-slow, test, etc).
- For deb repos, these are additional releases within a single repo
- Fpr rpm repos, each chanel is an entirely separate repo

## Mariner Repos
These repos are dedicated to the CBL-Mariner distro.
They have two "distributions", for example:
- `/yumrepos/cbl-mariner-2.0-prod-Microsoft-x86_64/`
- `/cbl-mariner/2.0/prod/Microsoft/x86_64`

## SQL Repos
These repos are for distributing SQL packages.
They're tied to a given distro/release and have symlinks similar to the shared/prod repos:
- `ubuntu/18.04/mssql-server-2017`

## Azurecore Repos
These are for first party use, predominantly SBI. They are identifiable by their name [^azurecore.*]. They only have a single distribution, and config packages are hosted on PMC ([example](https://packages.microsoft.com/repos/azurecore/pool/main/a/azure-repoclient-https-noauth-public-bionic/)).
