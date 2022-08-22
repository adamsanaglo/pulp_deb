# Azure Environment Creation
The intent of the script and yaml files in this directory is to provide a turn-key way to create
a new environment, running in Azure, that is scalable and secure.
Just by changing a few variables we should be able to create a PPE, tux-dev, and prod environment
that runs pmcserver and pulp.

## Required tools
As noted in the script, it depends on having the az cli and docker commands already
installed.
How exactly you want to do that depends on the details of your setup and whether you want to install
them in Windows or Linux, what distribution you're running, etc.
See the docs for installation instructions.
az cli: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

## Environment Description
The script currently creates an Azure Kubernetes Service cluster that will run instances of the
pmcserver container and a multi-container installation of Pulp, an Azure Database for PostgreSQL
flexible server instance that will serve as the database for both pmcserver and Pulp, a KeyVault
for managing secrets, and a container registry that we will push the container images into.

### Virtual Network
We create a private vnet and attach both the AKS and postgres instances to it.
This should ensure that all communication between the containers and each other or the database
is private.
There are two externally-available endpoints we make available (the "LoadBalancer" services in the
yml files), one allowing connections to the pmcserver api and another allowing connections to the
pulp-content containers.

### Pulp
The Pulp deployment closely follows the multi-container setup described by the [Pulp Operator
compose file](https://github.com/pulp/pulp-operator/blob/main/containers/podman-compose.yml).
This splits the Pulp application into three types of containers, each which we can run multiple
copies of, pulp-api, pulp-worker, and pulp-content.
The quay.io/pulp/pulp image has an entrypoint that expects you to tell it which one this container
is expected to be with the command arg, and then will run an appropriate script.

We will want to replace that pulp image with a similar one that:
1. We build ourselves and push to the container registry to comply with Microsoft's supply-chain
   security policy
2. Uses Azure Blob Storage as a storage backend. Currently I'm ignoring storage setup entirely
   and just using local storage on the AKS cluster.

### AKS
The AKS cluster creates a number of virtual machines, "nodes", which serve as the platform on which
it runs the containers we tell it to create.
We've specified the nodes should be created round-robin in each of the region's availability zones.
These nodes will be auto-scaled up or down depending on compute or memory demands.
I've set a minimum of two nodes and a max of six, but we can increase the max if need be.

A "Pod" is an AKS term for a set of containers that run together on the same node, and can
communicate via localhost.
We have created three pods so that network communication can be secret (localhost-only) without
bothering with certificates and encryption.
The "api-pod" runs a pmcserver and pulp-api container, the "worker-pod" runs a pulp-worker (and
soon) signing container, and the third "pod" is just a stand-alone pulp-content container.

As pods are created they'll be round-robin assigned to different nodes.
This ensures that if you have at least two instances of a pod running, they'll be running
in different availability zones.
The pods can also auto-scale in or out depending on cpu demand.
As initial parameters I've set a minimum of two pods for each, with a max of three for some pods
and max of 10 for more resource-intensive workloads.
The readiness probes defined on the network-facing containers ensures that they are not placed
into rotation until the services have started and they're listening for connections.

### Secrets
There are a number of secrets/passwords that are randomly generated and stored in KeyVault secrets.
These KeyVault secrets are then synced into AKS secrets so they can be used in env variables.
However this means anyone that can view the details of our AKS can retrieve the secrets if they
wanted to.
Anyone who is able to log in to a container will always have access to the secrets, as they are
injected as environment variables or config files for the services to use.
AKS is set up for secret autorotation, by default it polls for secret changes ever 2 minutes.
What should happen is that when a secret is rotated in the keyvault, AKS will notice and then will
do a rolling restart of the containers that use it so that they'll pick up the new secret.