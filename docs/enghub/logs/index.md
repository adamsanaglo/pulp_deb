# PMC Logs and Analytics

## Where PMC package download logs can be found

Access logs for downloads from repos managed by PMC are available in Kusto in the `csdups` cluster.

To use the cluster, you must first request access to [this security group](https://idweb.microsoft.com/IdentityManagement/aspx/groups/MyGroups.aspx?popupFromClipboard=%2Fidentitymanagement%2Faspx%2FGroups%2FEditGroup.aspx%3Fid%3Defe6a454-bec9-472b-8bc5-1c8836c73b7a) via IDWeb.

## Viewing raw log records

```kusto
cluster('csdups.kusto.windows.net').database('Repos').HttpAccessLog
| where PreciseTimeStamp >= ago(1h)
| take 20
```

## Sample log record queries

### Just rpm or deb packages, enriched with the region which served the download

```kusto
cluster('csdups.kusto.windows.net').database('Repos').HttpAccessLog
| where PreciseTimeStamp >= ago(1h)
| where path endswith_cs ".rpm" or path endswith_cs ".deb"
| extend ri_parts = extract_all(@"([a-z\d]+)", RoleInstance)
| Region = tostring(ri_parts[2])
| project PreciseTimeStamp, Region, path, code, size, totaltime
| take 20
```

### Downloads of a single package published to multiple shared repos

This query counts recent successful downloads of any package with "mssql-tools" in the path, extracts the delivery region which handled the request, and extracts the distro and version of the repo from which the package was requested.

```kusto
cluster('csdups.kusto.windows.net').database('Repos').HttpAccessLog
| where PreciseTimeStamp >= ago(1h)
| where code == "200"
| where path has "mssql-tools"
| extend ri_parts = extract_all(@"([a-z\d]+)", RoleInstance)
| extend path_parts = parse_path(path)
| extend d = split(path_parts.DirectoryPath, "/")
| extend OS = strcat_delim("-", d[1], d[2])
| extend PackageName = tostring(path_parts.Filename)
| project OS, PackageName, Region = tostring(ri_parts[2])
| summarize Downloads = count() by PackageName, OS
| order by Downloads
```

Please note the synthesized "OS" field is just a summarization of the path of the package within the repo.
The shared repos have two different path prefixes leading to the same content, reflecting the history and heritage of how various distros have organized their own package repos.
For example, the shared repo for Ubuntu 20.04 exposes the same packages under /ubuntu/20.04/ and under /repos/microsoft-ubuntu-focal-prod/.
