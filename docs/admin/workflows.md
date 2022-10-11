# Example Workflows

Note: these workflows assume you are in the `cli` folder of the Compute-PMC project.

## apt

```
# create a repo. Note: only legacy signing is available in dev environments.
pmc repo create myrepo-apt apt --signing-service legacy

# create a repo release
pmc repo releases create myrepo-apt jammy

# create a distro
pmc distro create mydistro-apt apt "some/path" --repository myrepo-apt

# upload a package
cp tests/assets/signed-by-us.deb .
PACKAGE_ID=$(pmc --id-only package upload cli/tests/assets/signed-by-us.deb)

# add our package to the repo release
pmc repo packages update myrepo-apt jammy --add-packages $PACKAGE_ID

# publish the repo
pmc repo publish myrepo-apt

# check out our repo
http :8081/pulp/content/some/path/
```

## yum

```
# create a repo. Note: only legacy signing is available in dev environments.
pmc repo create myrepo-yum yum --signing-service legacy

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
http :8081/pulp/content/awesome/path/
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
pip install --extra-index-url http://localhost:8081/pulp/content/mypypi/simple/ helloworld==0.0.1
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
http :8081/pulp/content/myfile/path/
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
