# PMC - packages.microsoft.com

Microsoft's mission, "to empower every person and organization on the planet to achieve more", allows we as Microsoft to meet customers where they are; whether that's Windows, MacOS, Android, or even Linux.
With that intent, Azure Compute/AzLinux/PMC team currently supports a set of environments to support package hosting for publishers targeting users running a Linux distribution.
This site describes details of these environments, and the processes to use the associated repositories (or create new ones) for publishing packages (whether new products or product updates) for Linux devices.

For payloads intended to be published to Windows clients, please visit the [https://aka.ms/ssdship](https://aka.ms/ssdship) page to learn more about the process for these types of packages.

The PMC service enables first party teams within Microsoft to publish Linux software packages to rpm (yum-compatible) and deb (apt-compatible) package repositories hosted under http://packages.microsoft.com.
The PMC team is also responsible for operating and maintaining the infrastructure which replicates and serves published packages, creating repositories, and managing publishing access to specific repositories.

## Documentation Applies Only to PMC v4

The documentation in the Engineering Hub (eng.ms) applies only to version 4 (v4 or "vNext") of the packages.microsoft.com publishing infrastructure.
This version of PMC is not yet in production; publishers can work with the PPE stamp of vNext by requesting access via service request.

All information about the current production PMC service can be found [here](https://aka.ms/pmcrepo).
