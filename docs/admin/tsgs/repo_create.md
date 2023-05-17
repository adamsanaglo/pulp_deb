# New Repository Creation

New Repo / Release creation is a fairly normal task that typically happens when a new version
of a supported distribution or product gets released.
Before you begin ensure you have the relevant information:

1. The desired endpoint(s) of the repo.
   There should be at least one "main" endpoint under `/[yum]repos/`, and possibly more "symlink"
   endpoints under the distro-specific top dirs, for example `/rhel/9/prod/`.
1. The desired variants / Releases.
   If creating something similar to another existing repo check what the existing repo has.
   * For yum repos this takes the form of creating multiple repos.
     - _Shared_ repos commonly have variants like `{name}-prod`, `{name}-insiders-fast`,
       `{name}-insiders-slow`, `{name}-testing`, and `{name}-nightly`.
     - _Dedicated_ repos commonly have variants based on supported distro, like `{name}-rhel9` and
       `{name}-sles15`.
   * For apt repos this takes the form of creating multiple Releases inside the Repo.
     - _Shared_ repos commonly have the release alias plus the common other variants, for example
       `trusty`, `insiders-slow`, `insiders-fast`, `nightly`, `testing`.
     - _Dedicated_ repos might have a dist for each supported distro, e.g. `jammy`, `trusty`,
       `focal`, and `bionic`.
1. The desired environment, TuxDev or Prod.
   You will do the remaining steps in this doc from a `pmc` cli that has access to the appropriate
   environment, which can be done from the `pmc-deploy` VM for Prod or `tux-ingest1` for TuxDev.
   Both will need to be accessed from a SAW.
1. A list of Accounts that should have access to the repo.

The repo name should follow the format`{main_endpoint}-{type}`, for example
`microsoft-rhel9.0-prod-yum`.
The type suffix is necessary to disambiguate some repos that have otherwise-identical names with
apt/yum variants.

> _NOTE_: On RHEL naming in particular  
> 
> We used to create "minor version" repos for RHEL, eg X.0, X.1, X.2, etc.
> No longer, now there is only one set of repos for the whole major version.
> However this has had carry-over effects on the repo naming conventions.
> To make matters worse RHEL 9 was done "wrong", before we had a clear idea of how this should look.
> Going forward:
> 1. There should be one set of "main" endpoints _with `.0` in the name specifically_.
>    For example "microsoft-rhel10.0-prod".
> 1. There should be one "symlink" endpoint _without the `.0`_.
>    For example "rhel/10/prod".
> 1. There should be a config repo _without the `.0`_.
>    For example "config/rhel/10/".
>
> It may be desirable to drop the `.0` from the main endpoint too, however there are some updates
> that would need to be made to the scripts in Compute-PMC/packages_microsoft_prod/ in that case.

The below will need to be repeated for each repo you have to create.

This doc assumes you have the following `pmc` profiles/permissions available:
| Profile Name | Permission    |
| ------------ | ----------    |
| [default]    | Repo_Admin    |
| package      | Package_Admin |
| account      | Account_Admin |

## If PMC v3 still exists and we are expecting to sync content between the two
1. Create the repo/release in v3 first by following this TSG:
   [Create Repo](onenote:https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/Shared%20Documents/General/Linux%20Repo%20Admins/TSGs.one#Create%20Repo&section-id={141D6D0F-3F3B-4599-8B63-2A78840930C5}&page-id={70EA69C6-E006-401B-9B44-343EAB7BE57E}&end)
   ([Web view](https://microsoft.sharepoint.com/teams/LinuxRepoAdmins/_layouts/OneNote.aspx?id=%2Fteams%2FLinuxRepoAdmins%2FShared%20Documents%2FGeneral%2FLinux%20Repo%20Admins&wd=target%28TSGs.one%7C141D6D0F-3F3B-4599-8B63-2A78840930C5%2FCreate%20Repo%7C70EA69C6-E006-401B-9B44-343EAB7BE57E%2F%29)).
1. Create a "Remote" in PMCv4 to tell it where the v4 repo should sync from.  
   `NAME` here should be the same as the repo name by convention, and the `--distributions` and
   `--architectures` options are required if this is an apt repo. Examples:
   ```
   $ pmc remote create microsoft-rhel9.0-prod-yum yum http://azure-apt-cat.cloudapp.net/yumrepos/microsfot-rhel9.0-prod
   $ pmc remote create microsoft-ubuntu-trusty-prod-apt apt http://azure-apt-cat.cloudapp.net/repos/microsoft-ubuntu-trusty-prod --distributions trusty,insiders-fast,insiders-slow,nightly,testing --architectures amd64,arm64,armhf
   ```

## Create the Repo
If we created a Remote in the previous step it can be linked to the newly created repo with the
`--remote` option.
We can create the Distributions (endpoints) at repo-creation time with the `--paths` option (if not
done now it can be done with `pmc distro create` later).
If v3 still exists _do not_ use the `--releases` option, we'll get to that later.
Examples:
```
$ pmc repo create microsoft-rhel9.0-prod-yum yum --remote microsoft-rhel9.0-prod-yum --paths yumrepos/microsoft-rhel9.0-prod,rhel/9/prod
$ pmc repo create microsoft-ubuntu-trusty-prod-apt apt --remote microsoft-ubuntu-trusty-prod-apt --paths repos/microsoft-ubuntu-trusty-prod,ubuntu/14.04/prod
```

## Create the Apt Release(s)
If PMCv3 still exists, _do not manually create a Release_.
Instead follow the above directions to create it in v3, create the Remote/Repo, and then
`pmc repo sync {name}` to auto-create the releases in v4.
`pulp_deb` has a longstanding issue with attempting to create duplicate Releases and then future
syncs failing with an error if you don't do it this way.

If PMCv3 _no longer exists_, then if creating a new repo you can and should create the releases
at the same time above by adding e.g. `--releases trusty,insiders-prod,etc` to the command.
Or, if you need to add a release to an existing repo, then you can do so, for example:  
```
pmc repo release create microsoft-ubuntu-trusty-prod-apt insiders-superfast
```

## Grant user access to new repo
Grant access to individual users:
```
pmc --profile account access repo grant <account_name_1>,<account_name_2> <repo_name_or_regex>
```
Or copy the permissions of a similar existing repo:
```
pmc --profile account access repo clone <OLD_REPO> <NEW_REPO>
```

## Update the apt-repos.txt file for Prod Apt Repos/Releases
If you added a new apt repo or release in production, you must also update the apt-repos.txt file.
This file is used by the mirrors to ensure they atomically sync apt repos, which have issues with
metadata tearing otherwise.
There [is a task](https://msazure.visualstudio.com/One/_workitems/edit/17960584) to update this
process to be less manual / more disaster-recoverable.

1. Fetch the current file.  
   ```
   $ wget https://packages.microsoft.com/info/apt-repos.txt
   ```
1. Edit it to add all the new endpoint/release combinations.
1. Push it back up and publish the repo.  
   ```
   $ ID=$(pmc --id-only --profile package package upload apt-repos.txt --type file)
   $ pmc repo package update info-file --add-packages $ID
   $ pmc repo publish info-file
   ```

## Create a config file repo for Prod Shared repos
If this is a new version of a Prod _Shared_ repo, e.g. a new version of RHEL or Ubuntu, then it
should have a config repo set up for it as well.

1. Create the config file repo. Example:  
   ```
   $ pmc repo create rhel_10-file file --paths config/rhel/10
   ```
1. Update the appropriate json file in Compute-PMC/packages_microsoft_prod to add information about
   this repo.
1. Generate the config files and setup packages and add them to the config repo.
   Exact steps TBD after we've actually done this once in v4.
1. Publish the repo.
   ```
   $ pmc repo publish rhel_10-file
   ```

## Done
Inform the requestor that you're done and give them the name of their new repo/release.
