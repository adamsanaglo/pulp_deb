# Linux Packaging
At Microsoft each product team is responsible for building and packaging their own software, however prior to May 2023 there was not much guidance provided on _how to do that_.
This documentation is intended as a guideline to help point people in the right direction.
See the sub-tabs for specific topics.

## PMC v4 Filename Changes
The PMC v4 infrastructure is fundamentally different under-the-hood in ways that should lead to better supportability and reliability and usability going forward.
However there are a couple of things that it does differently have have been causing problems with existing packages / tooling:

1. PMC v4 will rename your file to the "expected" format if you upload directly to it.
   (It will _not_ rename if your file is synced in from v3.)
    * `Name`-`Version`-`Release`.`Architecture`.rpm for RPMs.
    * `Name`\_`Version`\_`Arch`.deb for DEBs.
1. PMC v4 will de-duplicate packages that are identical (same checksum) in its backend.

As far as client tooling (`apt`, `apt-get`, `rpm`, `yum`, `dnf`, `zypper`, etc) goes, filenames in general _do not matter_. 
What they care about are the metadata fields as declared in the package itself, which is also what the PMC infrastructure pays attention to when building the `apt-get` / `yum` repository listings.
This is why the upstream project that PMC v4 is built on feels safe renaming and deduplicating the files.

However this has lead to a couple of problems.
You may have problems if:
* Your install scripts or reporting tooling is parsing the directory listing of PMC in order to find a particularly-named file.
  * The directory paths themselves are not guaranteed, and may change.
  * The filename will get changed if it does not conform to the standard.
* You are uploading the same file (identical checksums) with different filenames to multiple repos.
  For example to include a "centos8" or "el8" or "f32" in the filename.
  * If you're still uploading to PMC v3 and the packages are synced into v4 they'll get de-duplicated and one filename will "win" and appear everywhere.
  * If you're uploading directly to PMC v4 they'll get renamed outright.

### So What Should We Do?
In general:
1. Name your filenames according to the standard in the first place.
   This will help you and your tooling to not be surprised by the repo listings in PMC v4, but perhaps more importantly it will help ensure that the data you want is actually correct in the metadata fields, which are what _actually matters_ to the clients.
   If you really need "centos8" and "f32" in the filename, then it _should be_ in the metadata fields too.
   More on this in the package-type-specific sections.
1. Try to avoid depending on the html directory listings if at all possible.
   Directory listing doesn't even _need_ to be _turned on_ for repositories, though we do have it turned on for Customer convenience.
   What you can do instead is parse the actual repo data that `yum`/`apt-get` consume, because that is guaranteed to work and contain correct and expected data.
   In particular, look at the `Packages` files in apt repos and the "primary" file that `repomd.xml` references in yum repos.
1. If you have questions of course contact us.

## Building Per-Distro Packages
> I see packages with `el8` or `f32` or `~jammy` in their version.
> Do I need to build each package once for each distro/version?

That depends on your product.
In general you should build the most generic package that you can.

In some cases it is _necessary_ to build once for each distribution/version.
This would typically be because some dependency of your application has changes from one distro to another; a C lib changes ABI, or the python interpreter is different, or similar.
In such cases people would typically put the distro it's built for in the `Release` field of the rpm or `Version` of the deb to keep them separate (more on this the packaging sections).
My observation at Microsoft though is that here people tend to not depend on _anything_ on the system and build entirely self-contained binaries.
If the packages you're building are actually _the same_ (identical checksum), then there's no reason to build / sign / publish it more than once.
You could do it one time as long as you put that one file in all the repos where your users want it.

The same goes for architecture.
If your packages are not actually compiled down to binaries but rather interpreted by some interpreter and there is no difference between architectures, then there are the special "architectures" of `noarch` (rpm) and `all` (deb) that you can use to make one generic package that can be published everywhere. 