# Packaging RPMs
The RPM format and tooling is maintained primarily by Red Hat, and used not only by RHEL-adjacent distributions (CentOS, Fedora) but also by SLES, openSUSE, and our own CBL-Mariner.
It is a fairly opinionated compiled packaging format.
A compiled RPM consists of some binary headers containing metadata information, some installation / deinstallation scripts (which may just consist of putting files where you've specified if you haven't added anything else), and your actual software payload.
The correct tool to use to read or install an individual RPM is `rpm`, which is actually available on deb-based systems too.
The correct tool to use to build an RPM is `rpmbuild`, or something that wraps it.
The correct way to specify how to build an rpm is with a `.spec` file, or something that generates one.

There is already a lot of good documentation out there on how to build RPMs.
* [An RPM Packaging Guild](https://rpm-packaging-guide.github.io/)
* [The Fedora Packaging Tutorial](https://docs.fedoraproject.org/en-US/package-maintainers/Packaging_Tutorial_GNU_Hello/)
* [The Official RPM Reference Manual](https://rpm-software-management.github.io/rpm/manual/)

`rpm` by itself does not subscribe to repositories, so this is where package managers like `yum` (old RHEL-adjacent distros), `dnf` (new RHEL-adjacent distros), `zypper` (SLES / openSUSE), and `tdnf` (CBL-Mariner) come in.
These are all pretty inter-compatible tools, with the slight exception that `yum`/`dnf`/`tdnf` all put their `.repo` files in `/etc/yum.repos.d/` and `zypper` puts them in `/etc/zypp/repos.d/`.

## A Brief Overview of Relevant Spec File Fields
### Name
This _uniquely identifies_ the package, all packages with the same name will be considered different versions of each other.
Your package names should be specific enough that they won't accidentally conflict with anything else.

### [Optional] Epoch
The `Epoch` field, which is often not even mentioned, exists for the purpose of _changing versioning scheme_.
For example if you used to version by date and are switching to semantic versioning, how do you get the package manager to recognize that `2.0.0` is "newer than" `2022.12.31`?
You would do that by incrementing the `Epoch`.
`Epoch` has an implicit value of `0` if not specified, which it normally is not.

### Version
`Version` is typically used as the _upstream project version_, if applicable, or _product version_ if not.
Semantic versioning is recommended, so this is typically something like `1.0.0`.

### Release
`Release` is _how many times you have rebuilt / re-released this version_.
It typically starts at `1` and increments if you ever need to release an updated version without changing `Version`.
This would typically be because the upstream project version that you are packaging has not changed, but you added a bugfix patch or something locally.

`Release` is also where you will typically find a distro-version specifier like `el8` if you are building distro-version-specific packages.
This would _normally_ be done with the `%{dist}` macro, unless you have a Good Reason to do something different.
So a normal value for `Release` might look something like `1.%{dist}`.

`Epoch`/`Version`/`Release` when taken together is the "version" of your package (in that order).
So any package with a higher `Epoch` is "newer" than any version with a lower, and then it considers `Version`, and finally if both are the same it considers `Release`.

### Arch
Should be `noarch` if you do not need to build once per architecture, or one of the supported arches otherwise.

### URL
A good opportunity to point people to your upstream or product landing page.

### License
Please see [CELA's policies for releasing open source code](https://aka.ms/opensource) and [our FAQ on including license in packages](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/faq#packages-built-with-oss-components) for more information.
You of course don't _have_ to open-source your code to release to linux, but regardless of the license the process for including licensing information is the same.
PMC may start enforcing licensing checks in the future.

## Filename and NEVRA
The filename that `rpmbuild` generates will follow a `Name`-`Version`-`Release`.`Arch`.rpm format.
In general you should not modify that.
Also be aware that PMC v4 will rename your files for you if they do not follow that format.

The `N`ame `E`poch `V`ersion `R`elease `A`rch fields should uniquely identify exactly one signed, released RPM.
If you need to rebuild and release a new RPM then _something_ should change, usually Version or Release getting incremented.

## Dependencies
Declaring dependencies is covered in-depth in the packaging guides, but this is how the package managers know to install other packages when the user requests the one thing they care about.
Let's look at a current example with `amlfs`.

```
$ wget https://packages.microsoft.com/yumrepos/amlfs-el8/Packages/a/amlfs-lustre-client-2.15.1_24_gbaa21ca-4.18.0.147.0.2.el8.1-1.noarch.rpm
$ wget https://packages.microsoft.com/yumrepos/amlfs-el8/Packages/k/kmod-lustre-client-4.18.0.147.0.2.el8.1-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm
$ wget https://packages.microsoft.com/yumrepos/amlfs-el8/Packages/l/lustre-client-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm


# lustre-client
$ rpm -qp --queryformat '%{name}   %{version}   %{release}\n' lustre-client-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm
lustre-client   2.15.1_24_gbaa21ca   1.el8

$ rpm -qp --provides lustre-client-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm
lustre-client = 2.15.1_24_gbaa21ca-1.el8
lustre-client(x86-64) = 2.15.1_24_gbaa21ca-1.el8


# kmod-lustre-client
$ rpm -qp --queryformat '%{name}   %{version}   %{release}\n' kmod-lustre-client-4.18.0.147.0.2.el8.1-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm
kmod-lustre-client-4.18.0.147.0.2.el8.1   2.15.1_24_gbaa21ca   1.el8

$ rpm -qp --provides kmod-lustre-client-4.18.0.147.0.2.el8.1-2.15.1_24_gbaa21ca-1.el8.x86_64.rpm
kernel-modules >= 4.18.0-147.0.2.el8_1.x86_64
kmod-lustre-client-4.18.0.147.0.2.el8.1 = 2.15.1_24_gbaa21ca-1.el8
kmod-lustre-client-4.18.0.147.0.2.el8.1(x86-64) = 2.15.1_24_gbaa21ca-1.el8
lustre-client-4.18.0.147.0.2.el8.1-kmod = 2.15.1_24_gbaa21ca-1.el8


# amlfs-lustre-client
$ rpm -qp --queryformat '%{name}   %{version}   %{release}\n' amlfs-lustre-client-2.15.1_24_gbaa21ca-4.18.0.147.0.2.el8.1-1.noarch.rpm
amlfs-lustre-client-2.15.1_24_gbaa21ca   4.18.0.147.0.2.el8.1   1

$ rpm -qp --requires amlfs-lustre-client-2.15.1_24_gbaa21ca-4.18.0.147.0.2.el8.1-1.noarch.rpm
kernel = 4.18.0-147.0.2.el8_1
kmod-lustre-client-4.18.0.147.0.2.el8.1 = 2.15.1_24_gbaa21ca
lustre-client = 2.15.1_24_gbaa21ca-1.el8
```

The dependency system works by matching what a package `Requires` with other packages that `Provide` it.
`rpmbuild` will automatically add `%name = %version-%release`-style `Provides` (and sometimes others), but you can also add your own.
In this case we see that `lustre-client` and `kmod-lustre-client` provide themselves, and the `amlfs-lustre-client` requires those specific versions of those packages.
So Customers now only have to install the `amlfs-lustre-client` package and it will automatically install the other two.

If the amlfs team wants to provide a second version stream that does _not automatically update_ these existing packages but is still _not concurrently installable_ with them, they could do that by changing the names of the packages and adding a `Conflicts: OldName` "dependency".
