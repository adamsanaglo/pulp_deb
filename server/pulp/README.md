# Pulp Image

The intent here is to build our own docker image of pulp based on the `quay.io/pulp/pulp` image.
Microsoft's supply-chain security policy wants us to build everything (or as much as possible)
based off of CBL-Mariner and using known-good internally-built resources whenever available.
Building our own image also gives us the flexibility to apply our own patches if we need to.

## Updating Our Image

At some point we may need to rebuild the Dockerfile here or pull in additional work from
pulp-operator.
This section will explain how to generate a new copy of the upstream Dockerfile that you merge
with the one here.
You will need `ansible` installed.

1. In a fresh directory, clone the pulp-operator repository.
   ```
   git clone https://github.com/pulp/pulp-operator.git
   cd pulp-operator/containers/
   ```
1. Edit `vars/defaults.yaml` and comment out any images you don't care about and don't want to
   build.
   I left one image, pulp_stable_plugins_stable, and commented out all but three plugins, pulp-deb,
   pulp-rpm, and pulp-python.
1. Run `ansible-playbook build.yaml --verbose`.
   This will construct a Dockerfile and then use it to build the image.
1. Find the Dockerfile at `./images/pulp/Containerfile.core.pulp_stable_plugins_stable` and use it
   as the basis for updating our Dockerfile.
1. Copy over anything in `./images/pulp/container-assets/` because that gets built into the
   container.

## Differences From Upstream Image

1. The biggest difference is that instead of running on Fedora 36 (and python 3.10) we are building
   on CBL-Mariner (and python 3.9).
1. The 'dnf' command has been renamed 'tdnf' in CBL-Mariner.
1. Upstream relies on a dnf plugin that provides a "builddep" command to easily install the build
   dependencies of `createrepo_c`. tdnf does not work with that plugin, so I had to resolve and
   install a bunch of dependencies by hand to get `pulp-rpm` to install.
1. Here `pulpcore-manager` gets installed to `/usr/bin/` for some reason instead of
   `/usr/local/bin/`, so I had to create a symlink so things can find it.

## Building / Tagging / Testing

Once you have a workable Dockerfile build, tag, and test the image.

1. `cd server`
1. `docker build pulp/ --pull --tag localhost/pulp:stable`\
   If build is successful it will output a line like `naming to localhost/pulp:stable` at the end.
1. Optionally delete all untagged images if you have a bunch of leftovers from iterating on changes
   to the Dockerfile:\
   `docker rmi $(docker images | grep "^<none>" | awk "{print $3}")`
1. If it does not already, you can make `docker-compose.yml` use `localhost/pulp:stable` as the
   image for all pulp containers.
1. `make reset_rebuild`
1. `cd ../cli`
1. `./tests/simple_pulp_test.sh`
1. Ensure that the test repo was created and published with a package and repodata at
   [http://localhost:8081/pulp/content/test-repo/](http://localhost:8081/pulp/content/test-repo/)
