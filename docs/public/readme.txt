General
--------
This resource (packages.microsoft.com) is a collection of package repositories and related content (i.e. config files and keys).
This content is public by design. Directory browsing (aka "autoindex") is deliberately enabled for the convenience of our users.

Supported Interfaces
---------------------
The resources on packages.microsoft.com are meant for consumption by Linux packaging clients (apt, dnf, yum, zypper, etc).
In general, if you're just using a Linux packaging client to download/install packages, then you can stop reading here :)
This section summarizes which resources are intentionally static (and thus "safe" to depend on), which are subject to change,
and some recommendations for advanced usage.

Static/Supported Resources
- The paths to each repo's *metadata* (i.e. repomd.xml or Release/Packages for deb files) are static/supported.
- The paths to config files located under /config are static/supported.
- the paths to the key files under /keys are static/supported.

Resources that are subject to change
- The HTML/directory browsing interface is subject to change, and is not guaranteed to exist in perpetuity.
  - This includes the underlying structure of the HTML as well as the timestamp and filesize presented.
- The paths to individual packages are subject to change.
  - The repo metadata is the source of truth for a given package path if/when a change occurs.
- Repositories often have multiple copies of the same data in different formats. There's no guarantee that each format will be supported in perpetuity.
  - Deb repos *may* have Packages, Packages.bz2, Packages.gz, etc.
  - Rpm repos *may* have primary.xml.gz or primary.sqlite.bz2, etc
  - Package managers will generally prefer one of the above formats but accept a wide array of formats.
- The clamav signatures under /clamav will be deprecated in 2023.

Recommendations
- When possible, use the configuration files under /config and use standard Linux package managers.
- If you need to programmatically "find" a given package, without using a package manager, be sure to parse the metadata - *not* the html.
- Avoid depending on individual metadata files (i.e. primary.sqlite.gz, Packages.bz2), as these are subject to change.
  - Package managers handle this gracefully, by trying alternate files/formats.

Support/Contact
----------------
To report general issues or request support, please refer to https://github.com/microsoft/linux-package-repositories/issues
To report security issues, please refer to https://www.microsoft.com/en-us/msrc