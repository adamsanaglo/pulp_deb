# Packaging DEBs
The DEB format and tooling is maintained primarily by the Debian community and Canonical, and used in Debian-adjacent distributions like Ubuntu.
A DEB file is at the most basic level an `ar` archive that contains some specific content, including another archive of the actual binaries and a `control` file, which is a rough equivalent to an rpm `spec`.
`dpkg` is the tool that installs / interprets individual DEBs.
There are many competing building toolsets in the DEB world, including competing signing standards (Microsoft uses `debsig-verify`).

Here are some guides about building DEBs.
* [An Introduction to Debian Packaging](https://wiki.debian.org/Packaging/Intro)
* [The Ubuntu Packaging Guide](https://packaging.ubuntu.com/html/)
* [The Debian Package Management Reference Manual](https://www.debian.org/doc/manuals/debian-reference/ch02.en.html)

`dpkg` by itself does not subscribe to repositories, so this is where package managers like `apt-get` (older, more configurable) and `apt` (newer, simpler, more user-friendly) come in.
Repos are subscribed to by adding `.list` files in `/etc/apt/sources.list.d/`.

## A Brief Overview of Relevant Control File Fields
### Package
This _uniquely identifies_ the package's name, all packages with the same name will be considered different versions of each other.
Your package names should be specific enough that they won't accidentally conflict with anything else.

### Version
The single `Version` field in DEBs is a combined form of the `Epoch`/`Version`/`Release` fields in RPMs.
It takes the form `[Epoch:]Version[-Release]`, where the parts have the same meanings and purposes as the RPM equivalents.
A typical `Version` then might look something like `1.0.0-1`.

There are a _ton_ of special cases and conventions for the `Version` field [some of which are defined here](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version).
Of particular note is the practice of adding the distro-version's alias (like "jammy" or "bullseye") to somewhere in the Version or Release parts of the `Version`.
An example might look like `1.0.0-1~jammy`.
Where exactly it goes or what non-alphanumeric characters separate it doesn't actually matter very much as long as it doesn't change inside a given distro version.
This can help you disambiguate your packages if you need to build on each distro-version you are releasing to.

### Architecture
`all`, or the specific arch that this package is built for.

### Priority
All Microsoft packages probably should have a `Priority` of `optional`.
Higher priorities are reserved for things that _should_ or _must_ be installed at system-install time.

### Homepage
A good opportunity to link to your upstream or product landing page.

## License
Please see [CELA's policies for releasing open source code](https://aka.ms/opensource) and [our FAQ on including license in packages](https://eng.ms/docs/cloud-ai-platform/azure-core/azure-management-and-platforms/control-plane-bburns/pmc-package-ingestion/pmc-onboardingreference/faq#packages-built-with-oss-components) for more information.
You of course don't _have_ to open-source your code to release to linux, but regardless of the license the process for including licensing information is the same.
PMC may start enforcing licensing checks in the future.

## Filename and NVA
The expected filename of the build deb follows a `Package`\_`Version`\_`Architecture`.deb format.
In general you should not modify that.
Also be aware that PMC v4 will rename your files for you if they do not follow that format.

The `N`ame `V`ersion `A`rchitecture fields should ideally uniquely identify exactly one signed, released DEB, although this is not nearly as much of a strict expectation as it is in the RPM world.
However _inside a given repo_ there should not be any conflicts, so if you're releasing an updated version of a DEB you should increment the `Version` in some way.

## Dependencies
Information on declaring [dependencies](https://www.debian.org/doc/debian-policy/ch-relationships.html#binary-dependencies-depends-recommends-suggests-enhances-pre-depends) or [conflicts](https://www.debian.org/doc/debian-policy/ch-relationships.html#s-conflicts) can be found in the packaging guides.
Let's look at a current example with `amlfs`.

```
$ wget https://packages.microsoft.com/repos/amlfs-jammy/pool/main/k/kmod-lustre-client-5.15.0-1037-azure/kmod-lustre-client-5.15.0-1037-azure_2.15.1-24-gbaa21ca_amd64.deb
$ wget https://packages.microsoft.com/repos/amlfs-jammy/pool/main/a/amlfs-lustre-client-2.15.1-24-gbaa21ca/amlfs-lustre-client-2.15.1-24-gbaa21ca_5.15.0-1037-azure_amd64.deb
$ wget https://packages.microsoft.com/repos/amlfs-jammy/pool/main/l/lustre-client-2.15.1-24-gbaa21ca/lustre-client-2.15.1-24-gbaa21ca_1_amd64.deb


$ dpkg-deb -I lustre-client-2.15.1-24-gbaa21ca_1_amd64.deb
 Package: lustre-client-2.15.1-24-gbaa21ca
 Version: 1
 Architecture: amd64
 Conflicts: lustre-client

$ dpkg-deb -I kmod-lustre-client-5.15.0-1037-azure_2.15.1-24-gbaa21ca_amd64.deb
 Package: kmod-lustre-client-5.15.0-1037-azure
 Version: 2.15.1-24-gbaa21ca
 Architecture: amd64

$ dpkg-deb -I amlfs-lustre-client-2.15.1-24-gbaa21ca_5.15.0-1037-azure_amd64.deb
 Package: amlfs-lustre-client-2.15.1-24-gbaa21ca
 Version: 5.15.0-1037-azure
 Depends: lustre-client (= 2.15.1-24-gbaa21ca), linux-image-5.15.0-1037-azure, kmod-lustre-client-5.15.0-1037-azure (= 2.15.1-24-gbaa21ca)
 Architecture: amd64
```

Here we see the same information as the RPM example.
The `amlfs-lustre-client` package is requiring the specific matching-version `lustre-client` and `kmod-lustre-client` packages.
We're using slightly incorrect terminology to say that those are their names though, because unlike
in the RPM example here the packages names have _already_ been updated to include a specific version
(so these packages will not be seen as an upgrade to a generically-named `lustre-client` package)
and the old `lustre-client` package has been marked as a `Conflict` so they cannot be co-installed
on the same system.
