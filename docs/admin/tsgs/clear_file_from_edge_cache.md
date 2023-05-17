# Clear a File from Edge Cache
In general, packages are considered immutable.
A package Name/Epoch/Version/Release/Architecture (NEVRA) should correlate to one and only one package, with a consistent checksum.
Thus, our edge servers cache packages for 1 year, which offers some performance benefits for caching.
However, sometimes our publishers will delete and re-publish a package with different contents.
This violates the above principle and, more importantly, causes a customer-facing issue.
The "old" package will be "stuck" in cache until it expires, and customers will see **checksum mismatches**, because the metadata checksums will reflect the *new* package.
The steps here will help you purge this old file from cache, so that the correct file can be pulled in.

**Note**: The 1 year cache expiration applies only to packages.
Repo metadata is a [*completely different* situation](deb_metadata.md).

**Note:** These steps will remove the file from cache based on its **URL**, not its contents.
In other words, it will purge the *new* file from cache as well.
This is OK, as it will be re-fetched from origin/Pulp on-demand.

## Mitigation Steps
In order to proceed, you will need the URL path of the file that needs to be purged.
For example, this might be `https://packages.microsoft.com/repos/azurecore/pool/main/f/foo/foo.deb`
1. SSH to the `sark-apt-wus` jumpbox
2. Switch to the `apt-automation` user
3. Switch to the `~/src/Compute-PMC/edge/` folder
4. Sync the latest changes via `git pull`
5. Run the following command to purge the file from cache on all mirrors.
    * For the URL parameter, either of the following formats is acceptable
        * `https://packages.microsoft.com/path/to/file`
        * `/path/to/file`
    * The target can be any of the following
        * `all`: All mirrors (recommended)
        * `REGION`: An individual region (i.e. `wus, eus, etc`)
        * `REGION[1-4]`: An individual server within a region (i.e. `wus1, eus3, etc`)
```bash
$ ./purge-edge-cache.sh $URL all
```
5. Confirm that you can now pull the correct file from packages.microsoft.com (verifiable via checksum or file size)