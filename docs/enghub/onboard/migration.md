# Migration FAQ

This FAQ is to provide publishers with some information about how to migrate from the old v3 API
to the new v4 API.
It assumes that you have [a v4 account](~/onboard) and that you have already [set up the v4 CLI
tool](~/pmctool).


## How do I find my repo(s)?

The easiest way to find your repos using v4 is to search by their names:

```bash
pmc repo list --name-contains ubuntu-focal

pmc repo list --name-contains rhel9
```

Alternatively, you can look for repos by their path.
To do this, you need to look up the distro, which maps a repo to a particular path at
packages.microsoft.com.
Each distro will contain a `base_path` and `repository` which is the repository id in v4.

```bash
# find the repo at https://packages.microsoft.com/yumrepos/microsoft-rhel8.0-prod/
pmc distro list --base-path-contains "microsoft-rhel8.0-prod"

# find the repo at https://packages.microsoft.com/ubuntu/22.04/prod/
pmc distro list --base-path-contains "ubuntu/22.04/prod"
```


## I'm only seeing a limited number of results. How do I view more results?

Unlike the v3 API, the v4 API is paginated meaning that only a subset of results are displayed
(default is 100).
When querying for results, you should see something like this:

```json
{
    "count": 3543,
    "limit": 100,
    "offset": 0,
    "results": [
        # ...
    ],
}
```

The count field will tell you the total number of results.

To view more results, one option is to specify the `--offset` field.
You probably want to use a number like 100, 200, etc if your limit is 100.
The other option is to specify a larger `--limit` but be warned that if the number is more than a
couple hundred, you might run into problems.


## How do I upload my package to multiple repos?

In v3, a package had to be uploaded multiple times in order to be added to multiple repos.
In v4, a package needs to only be uploaded once before it can be added to multiple repos.
To give an example:

```bash
PKG_ID=$(pmc --id-only package upload mydeb_1.0_amd64.deb)
pmc repo package update myrepo1 jammy --add-packages $PKG_ID
pmc repo package update myrepo2 focal --add-packages $PKG_ID
```


## Are v4 operations synchronous or asynchronous?

In v3, when uploading a package, package uploads were processed asynchronously and a package result
was returned that could then be queried to get the status of the upload.
The v4 API works in much the same way, however, the v4 pmc client will by default automatically poll
the API for the upload task status until the task is completed.
If a task does not complete successfully and fails, the CLI will raise an error and return a
non-zero response code.

There is a `--no-wait` option that can be used to not wait if you don't want to poll the task (e.g.
`pmc --no-wait package upload ...`).
This applies to other operations such as the `pmc repo package update` command and the `pmc repo
publish` command.
You may, for instance, want to use `--no-wait` on the repo publish as publishing can take up to 30
minutes sometimes.

## How do I check the status of a task?

If you use the `--no-wait` option, you'll get back a json result with a task id such as
`tasks-016ccc9d-1621-48ba-80f2-e655ef6884ea`.
If you use the `--id-only` option in addition to `--no-wait` the CLI will return only the task id,
rather than a json object containing that id.

This task can be used to query the api using the task show command:

```
pmc task show tasks-016ccc9d-1621-48ba-80f2-e655ef6884ea
```

The task response will have a `state` field that will indicate the status of the task.
Depending on the task, the `created_resources` field will contain the newly created resource such as
the new package id when an upload is performed.
