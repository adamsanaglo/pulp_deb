# Config Packages for packages.microsoft.com
This directory contains files for building and releasing the packages (deb and rpm) that get
published to packages.microsoft.com to enable simple user configuration and enablement of the main
repos.
It also generates individual .repo or .list files, which are used if someone wants to
subscribe to a less-common repository.

## Configuring and Building
Some configuration is required, so you have to define the target in `[deb|rpm]/build_targets.json`.
A typical "build everything" job can be invoked by simply executing `build.sh`, but you can
also provide args to narrow that down more if desired.
For example:
* `./build.sh`
* `./build.sh rpm rhel 9`
* `./build.sh deb ubuntu 22.04`

### RPM Build Requirements
`jq` and `rpmbuild` must be installed to run the rpm build script.

### DEB Build Requirements
`jq`, `make`, and `lintian` must be installed to run the deb build script.

## Signing
You must sign the deb/rpm packages before releasing them in a non-dev environment.
It is expected that the release pipeline will do this step, and replace the initially built
packages with the signed versions.

## Releasing
The `./release.sh` script drives off the output of the `./build.sh` script, so if you only
build specific distros / versions then it will only consider those distros / versions for release.
It will create the file "config repos" if they don't already exist, push the built configs into it,
and create the "symlink" user-friendly distros that enable the (for example) "/rhel/9/prod" paths.

There is a `./release.sh --dev` option that will create the "shared" repos and any additional
repos that we should create "user friendly" symlinks for (driven by the config files), which is
useful for testing in your dev environment.
Otherwise if an expected "shared" repo is not available then its config repo and symlinks are
skipped.

### Release Requirements
It is expected that the `../cli` dir contains a current `poetry install` version of the pmc cli, and
`jq` must be installed.
It is also expected that the `~/.config/pmc/settings.toml` configuration has been set up so that
there are `Repo_Admin` and `Package_Admin` profiles, named `repo` and `package` by default, although
that's configurable (in `--dev` a second profile is not used and instead it switches permissions
with `../cli/update_role.sh`)

## Comparing With Prod
There is a helper script `./compare.py` that recursively examines symlink repos / config repos and
does some sanity checking with the .list and .repo files, comparing against current prod.
You can do a full clean comparison against prod by:
```
(cd ../server && make reset_rebuild)
../cli/update_role.sh Repo_Admin
./clean.sh
./build.sh
./release.sh --dev
./compare.py
```
