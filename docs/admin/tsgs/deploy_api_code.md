# Deploy API Code
These steps explain how to deploy the API code/containers for packages.microsoft.com.
1. Update the version in server/pyproject.toml and update the changelog by running:
    ```bash
    towncrier build --yes --version 1.0.0
    ```
2. Open a PR with your changes. You can see [this example PR](https://msazure.visualstudio.com/One/_git/Compute-PMC/pullrequest/8007633).
3. After merging all desired updates into `main`, [tag it](https://msazure.visualstudio.com/One/_git/Compute-PMC/tags) with a tag like `server-x.y.z` to match the release number.
4. This will trigger an Official build with [this job](https://msazure.visualstudio.com/One/_build?definitionId=265881&_a=summary). The output will be container images which can be deployed to various environments.

**NOTE**: To ensure you have the latest config changes, always ensure that whatever checkout you're working with is up to date by running `git pull`.

## Deploy to PPE
1. Check the release job to ensure the tag container has been pushed to the PPE ACR.
2. From an arbitrary system attached to corpnet, run update.sh as follows.
This will pull the latest containers from ACR and start them in PPE.
```bash
./update.sh ppe
```
**NOTE**: Images from each build are pushed to the PPE ACR, so the above step is all that's needed.

## Deploy to Tux-Dev
**NOTE**: Tux-dev resources are accessible only from corpnet.

**NOTE**: Since Expressroute is incompatible with AKS, the containers run on dedicated VM's using docker-compose.
1. Push the latest container images to the Tux-Dev ACR using this release job.
2. For each of the following tux systems
    a. SSH in from a corp IP (network access is restricted to Corp)
    b. Su to root (`sudo su - root`)
    c. Navigate to /root/src/Compute-PMC/tux-sync
    d. Run tux-sync.sh. (it is expected that the status check at the end will fail on tux-ingest-public)

|Server|IP|
|------|--|
|Tux-ingest1|10.169.23.70|
|Tux-ingest2|10.169.23.72|
|Tux-ingest-public|52.161.2.132|

## Deploy to Prod
1. Push the latest container images to the Prod ACR using this release job.
2. If necessary, submit a JiT request for the AME/prod subscription (ae06cb0d-47c5-420b-ac59-8e84bef194bb)
3. SSH to pmc-deploy (40.122.170.47)
4. cd to `~/src/server/deployment`
5. Run ./update.sh prod
6. Check the status of the deployment by running: `kubectl get pods`
