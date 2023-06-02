# Developing Pulp

In the course of our work we may find the need to change things in Pulp itself, and then submit
PRs upstream and/or build patches into our Pulp image.
The tooling and documentation in this directory exists to help with that process.
This will build and run a single-container version of Pulp directly from the upstream code.

## Setup

1. Create forks of the upstream projects to your github user.
    1. https://github.com/pulp/pulpcore
    1. https://github.com/pulp/pulp_deb
    1. https://github.com/pulp/pulp_rpm
    1. https://github.com/pulp/pulp_file
    1. https://github.com/pulp/pulp_python
    1. https://github.com/pulp/pulp-oci-images (Upstream for init scripts we add to the container)
    1. https://github.com/pulp/oci_env (Developer setup)
    1. https://github.com/pulp/pulp-openapi-generator (Required for tests)
1. Install `jq` if it is not already. (Required for tests)
1. Clone them locally in this dir `./clone-repos.sh <github_username>.

## Recommended Workflow

Pulp documentation describes the
[contribution guidelines](https://docs.pulpproject.org/pulpcore/contributing/index.html), but to
summarize and make some things more clear, the workflow I recommend is to:

### Developing
1. Create a working branch that tracks our image.
   In the following example we want to start work on a new branch in pulp_deb, which is currently
   version-locked in our Dockerfile to version 2.22.0, and we want to call the new branch something
   awesome.
   `./create-branch.sh 'pulp_deb' '2.20.0' 'new_awesome_branch'`
1. Do your development work.
1. `make build`
1. `make run`. Note: it returns fairly quickly but takes several minutes to actually become ready.
1. `./lint.sh <project>`. Runs lint commands *in the container*.
1. `./test.sh <project> [--setup] [<test_name>]`. "--setup" is required the first time after a
   rebuild to initialize test dependencies.
   For example:
   ```
   ./test.sh pulp_deb --setup test_sync_optimize_skip_unchanged_package_index
   ./test.sh pulp_deb test_sync_optimize_skip_unchanged_package_index
   ./test.sh pulp_deb  # runs all tests
   ```
   See [the docs](https://github.com/pulp/oci_env#debugging-functional-tests)
   for more information about debugging tests. Runs test commands *in the container*.
   > **NOTE:** Getting pulp tests to run locally currently seems finicky. 
   > Some tests seem to fail locally but _don't_ fail upstream, and it's unclear if that's expected.
   > Feel free to hack on it and make it better if you have time.
1. Test against `localhost:5001`.
1. If you need database changes:
   1. Make and apply your changes to the models above.
   1. Get a shell in the docker container. `make shell`
   1. Tell django to make a migration. `pulpcore-manager makemigrations --name <descriptive_name>`
   1. Apply it. `pulpcore-manager migrations`
   1. Since the container is mounting the source from disk, the migration will be available in the
      host repo checkout.
   1. Rebuild the image.
1. Create a patch for our pulp image by doing `./make-patch.sh <prefix> <project>`. 
   "Prefix" is the numerical prefix to the patch, so if we already have 10 patches for this project
   you want to make it "11".
   Reference it in Dockerfile.
1. Submit our PR, get feedback.
   * Alternately, push this branch up your github fork and point people to that so they don't have
     to attempt to review a patch.

### Upstreaming
1. Check out a new feature branch based on `upstream/main`.
1. Cherry pick over your change. Merge differences as necessary. 
1. If an Issue does not exist already describing the problem, create one in upstream repo.
1. You need to
   [create a file](https://docs.pulpproject.org/pulpcore/contributing/git.html#changelog-update) in
   the `CHANGES` directory named in the `issueNumber.issueType` format.
   The contents should be a 1-line description of the change.
   Usually copying the commit message is fine.
1. Amend it to your commit. They want a single commit in your feature branch.
1. The commit message should be something like:
   ```
   Description of the change.

   closes #123
   ```
   Where "123" is the Issue number.
   If an issue is really not necessary you can append "[noissue]" to the end of your commit issue.
1. Push the branch to your github fork and file a PR to merge branch into upstream `main`.
