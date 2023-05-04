# Deb Package Not Found in Metadata
Repository metadata depends on a hierarchy of files, with signatures and checksums to ensure consistency.
More detail on this topic can be found in the [checksum mismatch TSG](checksum_mismatch.md).
This arrangement has an inherent race condition, and deb repos are particularly vulnerable to it.

To mitigate this, we use a tool to proactively fetch deb metadata, ensure consistency, and store it under `/var/pmc/www` (outside of the pull-through cache).
On occasion, this can encounter an issue, which will cause metadata to be "stuck" out of date.
In this case, we have to force it to re-fetch metadata.
These steps will guide you through it.
1. Identify which repository is experiencing the issue.
    - This will likely be indicated by a Customer Reported Incident (CRI).
    - This can also be detected via this [Geneva Query](https://portal.microsoftgeneva.com/logs/dgrep?be=DGrep&offset=-1&offsetUnit=Hours&UTC=false&ep=Diagnostics%20PROD&ns=CSDUPSAPTLINUX&en=LinuxAsmSyslog&conditions=[["Msg","contains","Fetch:"]]&chartEditorVisible=true&chartType=line&chartLayers=[["New%20Layer",""]]%20).
    - This can also be detected via the [Status Monitor](https://pmcstatus.z19.web.core.windows.net/apt.html), though that does not scan *all* repos on *all* mirrors.
2. Login to the "sark-apt-wus" jumpbox.
3. Switch to the apt-automation account
    ```bash
    $ sudo su - apt-automation
    ```
4. Switch to the `/home/apt-automation/edge` directory
5. Identify which *mirrors* are affected.
    - For each mirror in `mirrors`, ssh in and run this command, populating `$repopath`, `$release`, `$arch`, and `$checksum` based on the findings from step 1.
        ```bash
        checksum=$(sudo sha256sum /var/pmc/www/$repopath/dists/$release/main/binary-$arch/Packages); if ! sudo grep -q $checksum /var/pmc/www/$repopath/dists/$release/Release; then echo "MISSING CHECKSUM"; fi
        ```
6. For each affected mirror, run the following command to mitigate.
    - If all mirrors **in a region** are affected, you can target the entire region (e.g. `wus`, `eus`, etc).
    - If **all** mirrors are affected, you can use `all` as the target.
    ```bash
    ./force-meta-update.sh ${mirror}
    ```
