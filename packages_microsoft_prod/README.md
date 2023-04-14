# Config Packages for packages.microsoft.com
This directory contains files for building the packages (deb and rpm) that get published to
packages.microsoft.com to enable simple user configuration and enablement of the main repos.
It also generates individual .repo or .list files, which are used if someone wants to
subscribe to a less-common repository.

## RPM Build Requirements
`jq` and `rpmbuild` must be installed to run the rpm build script.

## DEB Build Requirements
`jq`, `make`, and `lintian` must be installed to run the deb build script.

## Configuring and Building
Some configuration is required, so you have to define the target in `[deb|rpm]/build_targets.json`.
A typical "build everything" job can be invoked by simply executing `build.sh`, but you can
also provide args to narrow that down more if desired.
For example:
* `./build.sh`
* `./build.sh rpm rhel 9`
* `./build.sh deb ubuntu 22.04`
