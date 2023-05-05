# Removing a package from a repository

NOTE: Removing a package is, in most cases, a rare operation.
If a package is broken or problematic, in most scenarios the best action is to publish a newer version which corrects the problem.
Repos are often downloaded by outside entities for many reasons, and while those "repo cloners" will pick up new package versions, many will not remove a package that was removed from their upstream source.

Package removal looks very much like adding a package to a repo.
You will need to know the package ID of the specific package you want to remove, and you'll need to remove it from every repo to which you added it.

## Removing a package from a single repo version

```bash
pmc repo package update --remove-packages $PKG_ID $REPO_NAME
```

`$PKG_ID` can be a single package ID or a comma-separated list of package IDs.

## Removing all versions of a package

There is no command to remove all versions of a package from a repo.
Doing so presents the same problems as removing a single package version; cloned copies of the repo will retain them.
The best course of action is:
- Publish one final version of the package which simply notes the package has been withdrawn.
- Remove all older versions of the package
