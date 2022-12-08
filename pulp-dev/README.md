# Developing Pulp

In the course of our work we may find the need to change things in Pulp itself, and then submit
PRs upstream and/or build patches into our Pulp image.
The tooling and documentation in this directory exists to help with that process.

## Setup

1. Create forks of the upstream projects to your github user.
    1. https://github.com/pulp/pulpcore
    1. https://github.com/pulp/pulp_deb
    1. https://github.com/pulp/pulp_rpm
    1. https://github.com/pulp/pulp_file
    1. https://github.com/pulp/pulp_python
    1. https://github.com/pulp/pulp-oci-images (upstream for init scripts we add to the container)
1. Clone them locally in this dir `./clone-repos.sh <github_username>.

>**NOTE**
>
>It would be nice to create a python env that installs at least the pulp packages themselves so
>editors can do name-resolution, but I haven't had much luck getting that working.
>And full-on dev environments are hard to create, especially for `pulp_rpm`.
>If we're going to be doing a lot of development work in Pulp then it probably makes sense to just
>install [a real Pulp dev environment](https://github.com/pulp/oci_env).

## Recommended Workflow

Pulp documentation describes the
[contribution guidelines](https://docs.pulpproject.org/pulpcore/contributing/index.html), but to
summarize and make some things more clear, the workflow I recommend is to:

### Developing
1. Create a working branch that tracks our image.
   `./build-our-branch.sh 'pulp_deb' '2.20.0' 'new_awesome_branch'`
1. Do your development work.
1. Create a patch for our pulp image by doing `./make-patch.sh <number> <project>`. Reference it in
   Dockerfile.
1. Rebuild and test your local pulp image/containers.
1. Repeat as necessary until everything is working.
   The easiest thing to do is keep amending a single commit and rebuilding a single patch.
   If you need database changes:
   1. Make and apply your changes to the models above.
   1. Get a shell in a docker container. `docker exec -it pulp-api bash`
   1. Tell django to make a migration. `pulpcore-manager makemigrations --name <descriptive_name>`
   1. Copy the generated migration file to the appropriate place on your host.
      `docker cp pulp-api:<path> .`
   1. Amend your previous commit, rebuild the patch, rebuild the image.
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