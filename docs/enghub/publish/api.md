# PMC v4 API

While we provide [a CLI tool](~/pmctool) that should cover all operations package publishers need
to perform to manage their packages, we also have a REST API that publishers can use if needed.

This REST API can be accessed directly at <https://pmc-ingest.trafficmanager.net/api/v4/>.

## API docs

The REST API conforms to the [OpenAPI](https://www.openapis.org/) specification.
See the links below to view the REST API schema.

### redoc

<https://pmc-ingest.trafficmanager.net/redoc>

### OpenAPI

HTML:
<https://pmc-ingest.trafficmanager.net/docs>

JSON:
<https://pmc-ingest.trafficmanager.net/openapi.json>

## Authentication

In order to use the API, you'll need to provide an AAD token with each request.
Microsoft has some [general
docs](https://learn.microsoft.com/en-us/azure/active-directory/develop/msal-acquire-cache-tokens) on
how to do this.
However, there are a number of libraries such as [python's msal
package](https://github.com/AzureAD/microsoft-authentication-library-for-python) which can greatly
help in acquiring an MSAL authentication token.

Once you have the token, you will set the `Authentication` header of each request to `Bearer
<token>`.
