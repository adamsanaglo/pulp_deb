# Repository Metadata
This section is probably only relevant to you if you need to write an installer or similar that generates `.repo` or `.list` files or wants to parse the repository data that PMC generates for the package managers to consume.
Or if you're just insatiably curious.
The repository metadata boils down a list of packages available in the repo and all the relevant metadata they contain, including `Requires` and `Conflicts` information.

## A Brief Note on Signing
In the RPM-world it has historically been considered sufficient to only sign the RPMs themselves, not the metadata.
"I can verify that this RPM was created by someone I trust, so it's safe to install it, no matter where it happens to come from now" they figured.

In the DEB-world they have historically done the opposite; sign the repo metadata but not the DEBs.
"I trust this repository, so by extension I trust everything in it."

This is beginning to change in both places.
Microsoft, out of an abundance of caution and a commitment to supply-chain security, is going to always sign _both_ the packages _and_ the repodata.
Even if Customers (or Microsoft support personnel) are emailing individual packages to people, it will still be possible to verify that this is in fact a Microsoft package.
And Customers will also be able to verify that the repo package listing itself is actually what we intended and has not been modified.
PMC's public GitHub README [explains how to verify](https://github.com/microsoft/linux-package-repositories#signature-verification)
Microsoft's individual-DEB signatures.

## RPM Repositories
### Anatomy of a .repo File
A `.repo` file is essentially an `.ini` file, and ours will look something like this:
```
[unique-repository-label]
name=A human-readable repository name
baseurl=https://packages.microsoft.com/somewhere/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
sslverify=1
```

`yum`/`dnf`/`tdnf` all put their `.repo` files in `/etc/yum.repos.d/`, and `zypper` (SLES, openSUSE) puts them in `/etc/zypp/repos.d/`.

You can look up what those [fields mean](https://developers.redhat.com/articles/2022/10/07/whats-inside-rpm-repo-file#anatomy_of_a__repo_file) if you wish.
You can have multiple repo definitions in one repo file, and you can also have them _defined_ but _disabled by default_ if you set `enabled=0`.
If desired it is possible to temporarily enable a repo for a single command by doing `dnf install foo --enablerepo unique-repository-label` or similar.

### The Repo Matadata
RPM repos are flat, meaning that every client that enables this repo will have the same content available to it (the one exception being that there can be many package architectures in the repo that are not applicable to every system).
This repo file is instructing the package manager to look for a `repodata/repomd.xml` file under that `baseurl`.
And, since `repo_gpgcheck` is enabled, it will also look for a `.asc` GPG detached-signature, and verify that this `repomd.xml` file was in fact created by a trusted party.
The `repomd.xml` file is fairly small and just contains a list of other metadata files.
The "primary" file (whose exact name changes because it is prepended with its hash) contains the list of packages available in this repo and the url to find them.

So if your tooling wanted to know what packages were available in this repo (and where to download them from) it would ideally follow the same process.
This is the guaranteed interface for an RPM repo.
1. Download and parse `$baseurl/repodata/repomd.xml`
1. Download and parse the "primary" file.

## DEB Repos
### Anatomy of a .list File
A single repo listing in a `.list` file is only one line:
```
deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/SOMEWHERE/ RELEASE COMPONENT
```

`.list` files are stored at `/etc/apt/sources.list.d/`.
You can define multiple repos in one file.
The closest equivalent to defining a disabled repo is to simply comment it out with a `#`, but unfortunately there is no way to temporarily enable it like an RPM repo.
One workaround would be to define the list file somewhere it would _not be picked up by default_, and explicitly point the package manager to it with `apt-get update -o Dir::Etc::sourcelist=/path/to/repo.list` or similar.
[Or you can add and then immediately remove it](https://askubuntu.com/questions/1301894/how-can-i-enable-a-repository-or-target-temporarily-and-easily-disable-it-withou),
but that's the closest you can come.

This sample `.list` file expects Microsoft's public key to already be on the filesystem.
The `packages-microsoft-prod.deb` package (built and maintained by PMC) will install that key in that location.
If you cannot rely on your users having that package already installed you'll need to arrange for it to be put there.

### The Repo Matadata
DEB repos are _structured_, meaning that they provide different package listings to different clients depending on their `.list` configuration.
For example, if that `SOMEWHERE` in the url was `ubuntu/22.04/prod` and the `RELEASE` was `jammy`, `apt` would then look for a `/ubuntu/22.04/prod/dists/jammy/Release` file.
Since we are signing the repodata there is also an `InRelease` file, which is a GPG clearsigned version of `Release`, and a detached-signature `Release.gpg`.
Either can be used to verify that we generated the repodata.

The `Release` file specifies all of the `Packages` files (and their checksums) that are available in this repo, and then `apt` selects which ones it wants by filtering by `COMPONENT` (which in our case is always `main`) and architecture.
Note that you'll probably have to fetch _two_ `Packages` files to have a complete repo listing, the `all` architecture and the specific arch for this system.
Downloading and parsing those Packages files will give you the list of available packages and where to find them, and that's the behavior you should replicate if writing your own tooling.
