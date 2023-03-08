# CLI Docker container

We provide a Dockerfile that users can use so that the pmc-cli can be installed and used in a
Docker container. The main benefit of using a Docker container is that it provides an isolated
environment in which Python, the pmc-cli, and its dependencies can be installed.


## Building a CLI Docker image

To build your own Docker image, download a copy of [our
Dockerfile](https://msazure.visualstudio.com/One/_git/Compute-PMC?path=/cli/Dockerfile). Then cd
into the directory containing the Dockerfile and run:

```bash
docker build -t pmc-cli .
```

## Setup

In order to not have to specify options such as the MSAL settings each time you run the CLI, you
can mount a settings.toml file into the container.

To do this, first create a "pmc" directory that contains two files:
* settings.toml
* auth.pem

Your settings.toml file should look something like this:

```toml
[cli]
base_url=<url>
msal_client_id=<msal_client_id>
msal_scope=<msal_scope>
msal_authority=<msal_authority>
msal_cert_path=~/.config/pmc/auth.pem
```

We'll assume for the purposes of this doc that the absolute path to your pmc directory is
`/path/to/pmc`. If you already have a settings.toml at `/home/user/.config/pmc/settings.toml`
then you can simply use `/home/user/.config/pmc` in the next section.


## Running CLI commands

To run CLI commands, assuming you are mounting in a pmc directory:

```bash
docker run -t --volume "/path/to/pmc:/root/.config/pmc" --rm --network="host" pmc-cli repo list
```

We recommend setting up an alias:

```bash
alias pmc='docker run -t --volume "/path/to/pmc:/root/.config/pmc" --rm --network="host" pmc-cli'
```

Then you can run:

```bash
pmc repo list
```

## Uploading

In order to upload packages, you'll need to mount the packages into your docker container. We
recommend creating a folder and mounting it as a volume. The path you pass to the CLI will be the
path in the container and not the host filesystem.

```bash
docker run -t --volume "/path/to/pmc:/root/.config/pmc" --volume "/path/to/packages:/packages" --rm --network="host" pmc-cli package upload packages/mypkg.deb
```
