## Publishing

This document describes how to package and publish the CLI.

### PyPI

While we publish the pmc-cli package to packages.microsoft.com, there is an empty package on PyPI at
`https://pypi.org/project/pmc-cli/`. The purpose of this package is to reserve the pmc-cli name and
to prevent a nefarious actor from publishing their own pmc-cli package which our publishers might
accidentally install and use.

### Server Setup

These steps describe how to prepare the PMC server to distribute the CLI package. They assume that
your pmc client is setup using the repo admin credentials and that you want to distribute the
package at `pmc-cli`. They only need to be performed once per environment.

```
# create a repo named pmc-cli-python
pmc repo create pmc-cli-python python

# create a pypi distro called 'pmc-cli' that serves from a folder 'pmc-cli'
pmc distro create pmc-cli pypi pmc-cli --repository pmc-cli-python
```

### Packaging and Uploading

These steps assume you have your pmc cli set up using the pmc publisher account in production.

1. Open up pyproject.toml file and confirm that the version field is correct.
1. If it's not correct, update it and open a new PR with your change.
1. Once the PR is merged, create a new cli-x.x.x tag at <https://msazure.visualstudio.com/One/_git/Compute-PMC/tags>
1. Next run the following commands from your cli directory replacing x.x.x with your new version.

```
export VERSION="x.x.x"

git fetch -t
git checkout cli-$VERSION

poetry build

PACKAGE_ID=$(pmc --id-only package upload dist/pmc_cli-${VERSION}-py3-none-any.whl)

pmc repo packages update pmc-cli-python --add-packages $PACKAGE_ID

pmc repo publish pmc-cli-python
```

Now check `https://packages.microsoft.com/pmc-cli/` to ensure the package is there.
