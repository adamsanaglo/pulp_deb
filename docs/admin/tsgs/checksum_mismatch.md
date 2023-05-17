# Checksum Mismatch
The security of package repositories is built on a hierarchy of signatures and checksums.
Top-level files are signed with a trusted key, and contain checksums for the next tier of files.
This is fundamental to maintaining trust with our customers, and any issues here will block customers from installing packages.
Checksum mismatches come in two variations, but the commonality is that the **actual** checksum of a file doesn't match what's listed in the metadata one tier above that file:
- **Package Checksum Mismatch**: The checksums for one or more packages don't agree with the metadata.
- **Metadata Checksum Mismatch**: The checksums for one or more metadata files don't agree with those in other metadata files.

There is an inherent race condition in this system.
If a customer requests metadata while that metadata is being updated, they may find fetch artifacts that don't match.
However, this window is brief and such errors are typically transient.

## Deb Repo Hierarchy
- **InRelease**: Embedded signature, checksums for downstream files
    - **Packages(.gz)**: Contains checksums for individual packages
        - **.deb packages**: Individual packages installed by customers

## Rpm Repo Hierarchy
- **repomd.xml.asc**: Signature for `repomd.xml` file
    - **repomd.xml**: Contains checksums for metadata files, including `primary.xml(.gz)`
        - **primary.xml(.gz)**: Contains checksums for individual packages
            - **.rpm packages**: Individual packages installed by customers

## Troubleshooting
1. Identify which repo is affected.
This will normally be indicated by a Customer Reported Incident (CRI).
2. Determine if the issue resides centrally or only on the mirrors.
    - Check https://pmc-distro.trafficmanager.net/; see if the timestamps/checksums match what's present on https://packages.microsoft.com/.
    - If the checksums differ on pmc-distro, that could indicate a caching issue.
        - For **rpm repo metadata**, the cache will naturally update over-time, and the mismatch should mitigate itself.
        - For **deb repo metadata**, check the [deb Metadata TSG](deb_metadata.md).
        - For **packages**, refer to the [TSG to clear files from edge cache](clear_file_from_edge_cache.md).
3. Try to re-publish the repo, which will force the metadata to be regenerated.
    ```bash
    $ pmc repo publish --force $REPO_NAME
    ```