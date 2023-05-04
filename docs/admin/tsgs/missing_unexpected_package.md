# Missing or Unexpected Package
Publishers may, on occasion, reach out indicating one of the following:
- A published package does not appear in the repository
- A published package has a wrong/unexpected filename
- A published package appears in the "wrong" repository

There are multiple, overlapping causes for the above issues, and we will step through each of them.

## Pulp Package Naming
In some cases, Pulp will modify the filename of an uploaded package, causing publishers to think the package is "missing."
1. Each package (identified by unique SHA256 checksum) is stored *precisely once* in backing storage (Azure Storage Blob).
If a single package was published to multiple repos, with different filenames, the first filename will "win," and that filename will be used across all repos where  this package resides.
    - For instance, if a publisher uploads the same package to various RHEL/SUSE/etc repos, with distinct filenames, that package will have the same filename in all repos.
2. With the new API, Pulp will enforce package filenames to ensure consistency.
    - For deb packages, this is `name_version_arch.deb`
    - Fpr rpm packages, this is `name-version-release-arch.rpm`

Diagnosing this is fairly straight-forward
1. Track down the metadata for the affected repo
    - For deb repos, this will be the `Packages` file
    - For rpm repos, this will be the `primary.xml.gz` file
2. Search for the package name/version described by the publisher.
3. If the name/version are found, analyze the filename to determine if it matches what the customer expected.
4. Explain Pulp's file-naming semantics to the publisher, as described above.

## Package Uploaded to the Wrong Repo
Generally speaking, there's no instance where the PMC API will *put* a package in the wrong repo. Typically, the publisher simply mixed their build/release jobs incorrectly, causing artifacts from build `foo` to land in repo `bar`.

Use the steps in the [Fetch API Logs TSG](fetch_api_logs.md) to inspect the API logs and determine to which repo the package was published, using filenames and timestamps to assist.