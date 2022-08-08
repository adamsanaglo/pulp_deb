# pmcstatus

CLI with helpful tools for managing the PMC status site.

### Development
```
cd status/cli/
pip install -e .
```

## Usage

To get a list of commands and options:

```
pmcstatus --help
pmcstatus publish --help
```

### Examples

```
# Publish the status of the artful dist in the azure-cli apt repository to the PMC Status Site.
pmcstatus publish -t apt -r https://packages.microsoft.com/repos/azure-cli --dists artful -n pmc-scan-repos

# Publish the status of the vscode yum repository to the PMC Status Site.
pmcstatus publish -t yum -r https://packages.microsoft.com/yumrepos/vscode -n pmc-scan-repos
```

### Notes

- When supplying the repository url, make sure that it matches exactly what is on the website. If there is, for example, an extra '/' at the end, then it will create a new entry in the status site.

- Extraneous entries in the status site created by incorrectly typing the url will be cleared when a full repository check is run and repositories and dists are filtered. 

- `pmcstatus publish` will prompt for a master key. This can be found in the function app's portal under 'App Keys->Host Keys'. Copy the `_master` key. 