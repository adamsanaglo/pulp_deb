# Example Workflows

Note: these workflows assume you are in the `cli` folder of the Compute-PMC project.

## apt

```
# create a repo
pmc repo create myrepo-apt apt

# create a repo release
pmc repo releases create myrepo-apt jammy

# create a distro
pmc distro create mydistro-apt apt "some/path" --repository myrepo-apt

ASSETS_PATH=cli/tests/assets
# upload a binary package
DEB_PACKAGE_ID=$(pmc --id-only package upload $ASSETS_PATH/signed-by-us.deb)

# upload a source package
DEBSRC_PACKAGE_ID=$(pmc --id-only package upload $ASSETS_PATH/hello_2.10-2ubuntu2.dsc --source-artifact $ASSETS_PATH/hello_2.10.orig.tar.gz --source-artifact $ASSETS_PATH/hello_2.10-2ubuntu2.debian.tar.xz)

# add our package to the repo release
pmc repo packages update myrepo-apt jammy --add-packages $DEB_PACKAGE_ID,$DEBSRC_PACKAGE_ID

# publish the repo
pmc repo publish myrepo-apt

# check out our repo
http :8081/some/path/
```

## yum

```
# create a repo
pmc repo create myrepo-yum yum

# create a distro
pmc distro create mydistro-yum yum "awesome/path" --repository myrepo-yum

# upload a package
cp tests/assets/signed-by-us.rpm .
PACKAGE_ID=$(pmc --id-only package upload signed-by-us.deb)

# add our package to the repo release
pmc repo packages update myrepo-yum --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish myrepo-yum

# check out our repo
http :8081/awesome/path/
```

## python

```
# create a repo
pmc repo create mypyrepo python

# create a distro
pmc distro create mypypi pypi mypypi --repository mypyrepo

# upload a package
PACKAGE_ID=$(pmc --id-only package upload tests/assets/helloworld-0.0.1-py3-none-any.whl)

# add our package to the repo release
pmc repo packages update mypyrepo --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish mypyrepo

# check out our repo
pip install --extra-index-url http://localhost:8081/mypypi/simple/ helloworld==0.0.1
```

## file

```
# create a repo
pmc repo create myfile file

# create a distro
pmc distro create myfile file myfile/path --repository myfile

# upload a package
PACKAGE_ID=$(pmc --id-only package upload --type file tests/assets/hello.txt)

# add our package to the repo release
pmc repo packages update myfile --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish myfile

# check out our repo
http :8081/myfile/path/
```


## syncing

```
# create a remote
pmc remote create microsoft-ubuntu-focal-prod apt "https://packages.microsoft.com/repos/microsoft-ubuntu-focal-prod/" --distributions nightly

# create a repo
pmc repo create microsoft-ubuntu-focal-prod apt --remote microsoft-ubuntu-focal-prod

# sync
pmc repo sync microsoft-ubuntu-focal-prod
```
