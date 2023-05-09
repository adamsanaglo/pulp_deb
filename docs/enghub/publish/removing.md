# Removing a package from a repository

Package removal looks very much like adding a package to a repo.
You will need to know the package ID of the specific package you want to remove, and you'll need to remove it from every repo to which you added it.

## Frequently asked questions

[!INCLUDE [remove-faq](../include/remove-faq.md)]

## Removing a package version from a single repo

If you don't know the name or id of your repo, you can search for it with the list command:

```bash
pmc repo list --name-contains myrepo
```

Likewise, you can use the package list commands to find the id of your package:

```
# deb package
pmc package deb list --name mydebpackage --version 4.2.1

# rpm package
pmc package rpm list --name myrpmpackage --version 1.2.3
```

Once you have those, you can use:

```bash
pmc repo package update --remove-packages $PKG_ID $REPO_NAME
```

`$PKG_ID` can either be a single package ID or a comma-separated list of package IDs.

## Removing all versions of a package

There is no command to remove all versions of a package from a repo.
Doing so presents the same problems as removing a single package version; cloned copies of the repo will retain them.
The best course of action is:
- Publish one final version of the package which simply notes the package has been withdrawn.
- Remove all older versions of the package
