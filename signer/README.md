ESRP Signing Container
-----------

Metadata for packages.microsoft.com needs to be signed by a trusted entity.
ESRP holds the trusted signing keys, and has an API for signing content.
This API is invoked using `az xsign`. The code in this container uses
`az xsign` to initiate ESRP signing and to send the resultant signatures
to the requestor.

**NOTE**: Per the docs (linked below) Pulp will only request *detached* signatures. Presumably it has its own mechanism for generating an "attached" signature (file contents with signature appended).

Workflow
--------
1. Requestor (Pulp) POSTs an unsigned metadata file to the `/sign` endpoint of this API.
    - For apt, this is the `Release` file
    - For yum, this is `repomd.xml`
2. This API responds with a `200` and the following header, which is unique to this request.
    - `{"x-ms-workflow-run-id" : "08585553379884705257669549339CU53"}`
3. This API performs the following steps:
    - Generate an ESRP Config JSON file which defines the parameters for signing
        - One parameter is a "request signing certificate" which resides in keyvault. `az xsign` will download this for us in an upcoming step.
    - Use MSI to download the authentication cert for a Service Principal
    - Login to `az cli` using that service principal
    - Run `az xsign` to sign the unsigned file
    - `az xsign` writes the signature to a file on disk.
    - Read the detached signature from file
4. Requestor (Pulp) polls the `/signature` endpoint for status, using the ID from step 2.
    - A `400` is served if the request ID is invalid.
    - A `204` is served if the request is still processing.
    - A `200` is served, along with the signature bytes, if the request is complete.
    - A `500` is served if the server encountered a fatal error signing this request.
8. Requestor (Pulp) inserts the artifacts into the appropriate repos and proceeds to publish them.

Reference
---------
[Pulp Metadata Signing](https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html)
[az cli xsign client](https://github.com/microsoft/Sign.Client.AzCli)