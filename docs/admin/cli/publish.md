# Publishing

This document describes how to publish the CLI.

## PyPI

While we publish the pmc-cli package to our Azure Artifacts feed, there is an empty package on PyPI
at `https://pypi.org/project/pmc-cli/`. The purpose of this package is to reserve the pmc-cli name
and to prevent a nefarious actor from publishing their own pmc-cli package which our publishers
might accidentally install and use.

## Azure Artifacts

In order to manage packages in the Compute-PMC feed, you'll need to be a feed Contributor, Owner, or
Administrator. By default the PMC team in ADO has Owner access to the Azure Artifact feed. If you
are not on the PMC team or wish to customize your role/permissions, visit [the feed permissions
setting page](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/settings/permissions).

## Releasing

1. First, identify the version you want to publish and export it (`export VERSION="x.x.x"`)
1. Open up `cli/pyproject.toml` and update the version field if necessary.
1. Next, update the changelog with `towncrier build --yes --version $VERSION`.
1. Go to server/app/core/config.py and bump `MIN_CLI_VERSION` if necessary (e.g. if there's a
   backwards incompatible server change or security fix)
1. Open a PR with your changes and get it merged.
1. Once the PR is merged, create a new cli-x.x.x tag at <https://msazure.visualstudio.com/One/_git/Compute-PMC/tags>
1. Now monitor [the build pipeline](https://msazure.visualstudio.com/One/_build?definitionId=312903)
1. After the build is done, on the build page click 'Releases' and then the associated release.
1. The release should automatically push to PPE. Manually start a Production push as well.
1. Go to [our Azure Artifact
   feed](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/versions/),
   find the latest version and click the "Promote" button to promote it to a "Release". If you
   aren't able to promote the package version, see the setup section of this doc.
