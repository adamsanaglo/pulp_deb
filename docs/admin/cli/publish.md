## Publishing

This document describes how to package and publish the CLI.

### Server Setup

These steps describe how to prepare the PMC server to distribute the CLI package. They assume that
your pmc client is setup for the environment and that you want to distribute the package at `pypi`.
They only need to be performed once per environment.

```
# create a repo named pypi-python
pmc repo create pypi-python python

# create a distro pypi that serves from a folder 'pypi'
pmc distro create pypi pypi pypi --repository pypi-python
```

### Packaging and Uploading

These steps assume that your pmc client is set up for the environment from which you want to
distribute the pmc cli package.

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

pmc repo packages update pypi-python --add-packages $PACKAGE_ID

pmc repo publish pypi
```
