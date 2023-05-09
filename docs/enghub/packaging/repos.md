# Repositories: How Your Customers Get Your Packages
> So I've built our packages, signed them with ESRP, and released them with PMC.
> What next?
> Do I just paste a link to the rpm/deb in our documentation?"

In general, no, you should not do that.
That may be acceptable if your software is Edge, or something else that has its own update mechanism built-in.
In general though the linux world operates on the bases of subscribing to repositories that they want to consume packages out of, and then they have client-side tooling to search for and install particular things that they care about.
This is the same way phone app stores works except you're not limited to the Apple / Google stores, in the linux world you can easily add other repos to expand the list of available software.

This has a few benefits:
* The repositories we publish contain the information required for their systems to verify that the packages have been correctly signed by Microsoft.
  This is the linux-world equivalent of the UAC screen that pops up in Windows asking if "you're sure you want to allow this Publisher to modify your device?", except that the permission is granted once per publisher when the user installs our public key.
* Updates you publish are automatically available.
  Client machines will periodically check for updates (typically about once per day) and prompt the users to upgrade if there are updates.
  Some users even have their machines set to automatically upgrade whenever there is an update available.
* Other software in the same repo is available and discoverable.
  If someone enables our Ubuntu Jammy repo because they need to install dotNET runtime, then that's great and they can get it.
  If they later decide they also want PowerShell, then it's already available and it's one command or a couple clicks away, no additional setup required.
* It gives you the Publisher the ability to split your software amongst multiple packages if that makes sense.
  To go back to the dotNet example, there's a `dotnet-runtime` package, but also `dotnet-sdk` and others.
  `dotnet-runtime` is installable alone, but if you want `dotnet-sdk` then it will automatically pull in `dotnet-runtime` too.
  This gives your customers the ability to install only what they need, without having to deal with a monolithicly-large installer that asks you to check boxes to select what you want to install (which is not really a thing in linux anyway).

## Managing Repositories as a Publisher
### What Types of Repos Are There?
The full list of existing repositories can be viewed by directly examining the packages.microsoft.com website.
Two package/repo formats are currently supported.

- apt (Debian-style "deb") repos: <http://packages.microsoft.com/repos/>
- yum (RHEL-style "rpm") repos: <http://packages.microsoft.com/yumrepos/>

Within each of the above categories, there are two *types* of repositories.
* **"Shared"** repositories, which serve as a "one-stop shop" for customers to get any software for their distro (i.e. Debian 11 or RHEL 9).
    * The repo for a new release of a distro is generally created during the final beta testing phase of the release.
* **"Dedicated"** repositories, which contain content for a specific product.
    * These are typically used if the published packages may conflict with or break user scenarios.
      Users must "opt in" to the potentially breaking behavior by enabling this repository.

### Creating Repos / Gaining Access to Repos
Please read [this short section of the onboarding doc](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/onboard#request-publishing-access).

### Publishing Packages to Repos
This is covered in detail in the [publishing doc](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/publish).
In short it is a three-step process:
1. Uploading your signed packages to PMC.
1. Adding the packages to the repo(s) they should be available in.
1. Publishing the repo(s) to make your changes public.

## Enabling Repositories As A Customer
The PMC team provides some configuration files / packages that Customers can use to easily enable some repos.
If you look at [packages.microsoft.com/config/](https://packages.microsoft.com/config/) you can navigate deeper to find config files relevant to your distro / version.
For example, on RHEL 8 I can go to [/config/rhel/8/](https://packages.microsoft.com/config/rhel/8/) and find a few things:
* A `packages-microsoft-prod.rpm` (or deb, on deb-based distros).
  Installing this package enables the "prod" repo for your distro, in this case [/rhel/8/prod/](https://packages.microsoft.com/rhel/8/prod/) which is itself a customer-convenience alias to [/yumrepos/microsoft-rhel8.0-prod/](https://packages.microsoft.com/yumrepos/microsoft-rhel8.0-prod/), which is where your packages go if you publish them to the **shared** repo `microsoft-rhel8.0-prod-yum`.
* In addition to the package there is also a `prod.repo` file (or .list, on deb-based distros).
  Enabling that is equivalent to installing the `packages-microsoft-prod` package.
  There are also `insiders-fast` and `insiders-slow` and `testing` files which subscribe you to the appropriate variants of that **shared** repo.
  If your customers want to be subscribed to one of those then they can and should also be subscribed to the `prod` repo.
  The Microsoft Defender team already has some great documentation on [how to use these files](https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/linux-install-manually?view=o365-worldwide#configure-the-linux-software-repository) on different distros, so I won't duplicate it here.
* In this case there are also some additional repo configurations available for some **dedicated** SQL Server repos, which can be enabled the same way as those above.

### Repository Configuration Q & A
* > How would I as a Publisher know whether I need to request my own **dedicated** repo?

  _Most_ software should go into the **shared** repos, however there are some trade-offs:
  1. There is a non-zero amount of work required to continuously push your software into the new **shared** repos as new distro versions are released.
     This is something that the PMC team could help automate if it is a requested-enough feature from Publishers.
  1. Software in the **shared** repos is assumed to be co-installable, which means that if you are depending on specific versions of other packages in our repos your dependencies must not conflict with anything else in the repo.
     For example if your require `foo` version `1`, and someone else publishes software requiring `foo` version `2`, customers who want both pieces of software are going to have dependency conflicts.
     This is not _typically_ a problem at Microsoft because teams here tend to build mostly self-reliant software that does not depend on a lot of "common" packages.
     However if it is going to be a problem for you then a **dedicated** repo is the correct choice.
  1. Repositories as version management.
     To go back to the SQL Server example, they have published repos for SQL Server 2017, 2019, and 2022, all into separate repos.
     This setup gives Customers the ability to enable the repo of the product version they actually want, without fear that their servers will accidentally upgrade from 2017 -> 2022 as part of its regular software update process.
     The alternate (and preferred) way to accomplish the same thing in the **shared** repos is to _name_ your packages something like `mssql-server-2017` (all in the _name_ field, not the _version_ field(s), more on this in the packaging sections).
     Then the different versions of your software can co-exist in one repo without conflicts.
     This breaks the presumption of co-installability mentioned above, however that's okay because no reasonable Customer would assume that you could install both `mssql-server-2017` and `mssql-server-2022` at the same time on the same machine.
     And you can actually prevent an _unreasonable_ Customer from trying it by declaring Conflicts in your packages (again, more on that in the packaging sections).
     This same potential conflict exists with **dedicated** repos because an _unreasonable_ Customer might try to enable both the 2017 and 2022 repos.
  1. Historically permissions have been managed at a per-repo level, so there had been concerns about other people being able to delete your software out of the **shared** repos.
     This is no longer an issue in PMC v4; the account that publishes a package is the only one (except the PMC team, or the owning team for the dedicated repo (e.g. Mariner team for the Mariner repos)) who can delete it or publish a new version.
* > How can my customers enable my **dedicated** repo for which PMC doesn't provide config files?

  You can create your own or write an installer that creates them fairly easily.
  The azure-cli team already has some excellent documentation on [how to do this.](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux)
* > How can I get the PMC team to generate the config files for us like they are doing for SQL Server in the RHEL 8 example above?

  Just ask us.
  We'd need to know what versions of what distros you plan to support so we can generate config files in the appropriate places.
