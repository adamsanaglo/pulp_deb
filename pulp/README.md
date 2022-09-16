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

## Signing Repodata
At a "10,000 ft view" the way repodata signing is supposed to work in Pulp is that you have some
local script that Pulp can call out to, you register it with
`pulpcore-manager --add-signing-service`, and then you reference its `pulp_href` url when creating
a repo (yum) or when publishing content (apt).
Additionally yum/apt repos want different signing services that do slightly different things.
If you have it all set up properly then Pulp will sign and publish signatures as part of the
`publish` step.

In our case, we have two fundamentally different types of signing that we need to be able to do.
"Legacy" signing is done locally in the `signer` container using the MS Open Tech key.
"ESRP" signing authenticates with an auth cert and then calls out to `az xsign` to get ESRP to sign
the files with the secret key that only they have access to.
There is also a "test ESRP" signing process that uses a different key that the PPE is expected to
be using to test things.

The `sign_cli` directory contains the 3 public keys (legacy, test-esrp, prod-esrp) and 6 signing
scripts (public keys * (yum, apt)) necessary for signing in various environments.
They expect the `signer` container to be available at `http://localhost:8888`, if it is available
on a different hostname you must write a local `.env` file that contains a `SIGNER_HOST=whereever`
configuration.
*Nothing currently registers these as signing services automatically.*

When you register a signing service, Pulp will execute a test signature to ensure that the return
value is what it expects and it is in fact signed by the correct public key.
That means it would call out to ESRP to execute a test signature - which can be a slow process - and
which would delay the startup of whatever container was attempting to ensure the signing services
were registered as part of the startup script.
And in our current setup there is no easy way to call out to the database to check if they're
already registered.
`pulp-worker` is the one that has access to the `signer` container and so must register the signing
services, but it *doesn't* have access to `pulp-api`, and `pulpcore-manager` does not currently have
a "check to see if signing service is already registered" command, and any other solution would be
fragile in the face of pulp internals changing.
Instead it is expected that someone will manually register the signing services when an
environment is created, which should be fine since this is a once-per-environment step.

The three args to `add-signing_service` are the name, the signing script, and the fingerprint
of the expected public key.
The public key must be imported to gpg.
The command must be executed from a container that has visibility to the `signer` container, which
in our case is only `pulp-worker`.

### Example Yum Signing Service Registration
[https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html](https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html)
```
gpg --import /sign_cli/msopentech.asc
/usr/local/bin/pulpcore-manager add-signing-service "legacy_yum" /sign_cli/sign_legacy.py "$(gpg --show-keys /sign_cli/msopentech.asc | head -n 2 | tail -n 1 | tail -c 17)"
```

### Example Apt Signing Service Registration
[https://docs.pulpproject.org/pulp_deb/feature_overview.html#metadata-signing](https://docs.pulpproject.org/pulp_deb/feature_overview.html#metadata-signing)
```
gpg --import /sign_cli/msopentech.asc
/usr/local/bin/pulpcore-manager add-signing-service "legacy_apt" /sign_cli/sign_legacy_apt.py --class deb:AptReleaseSigningService "$(gpg --show-keys /sign_cli/msopentech.asc | head -n 2 | tail -n 1 | tail -c 17)"
```
