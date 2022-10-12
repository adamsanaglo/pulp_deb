# PMC Client
The new client has an experience that is similar to `repoclient` but with some new features.

## Sample Configs
- Tuxdev: [sample-tuxdev.toml](sample-tuxdev.toml)
- Prod: [sample-prod.toml](sample-prod.toml)

## List Resources
```
# List Repositories:
pmc repo list

# List all .deb Packages
pmc package deb list

# List all .rpm Packages
pmc package rpm list

# List the Packages in a Repo:
pmc repo package list $REPO_NAME

# Responses are paginated, so you'll only receive the first 100 responses by default
# Use --offset to see the next "page" of resources
pmc repo list --offset 100

# Use --limit to change the number of returned resources
pmc repo list --limit 50
```

## Add/Remove Packages
```
# Upload a package
pmc package upload [FILE]

# Add one or more packages to a repo
pmc repo package update --add-packages $PKG_ID;... $REPO_MAME [$RELEASE]

# Remove one or more packages from a repo
pmc repo package update --remove-packages $PKG_ID;... $REPO_NAME [$RELEASE]
```