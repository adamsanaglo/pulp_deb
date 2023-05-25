# Fetching API Logs
These steps explain how to fetch logs for API and other central services.
Logs are shipped to Geneva/DGrep for analysis.

- Navigate to [Geneva](https://portal.microsoftgeneva.com/s/4B85A28B)
    - If the above link fails, select:
        - **Endpoint**: Diagnostics Prod endpoint
        - **Namespace**: PMClogs
- Select the pertinent "events" (AKA containers)
    - See table below for more detail
- Select the relevant timeframe for this search
    - DGrep is *slow*, should use a brief time window (hours) if possible.

|"Event"|Purpose|
|-------|-------|
|NginxApi|Nginx *proxy* that handles TLS termination for our API|
|Pmc|Our API logs (generally  the most useful)|
|PulpApi|The Pulp API logs (the backing API for PMC)|
|PulpWorker|Repo building/metadata creation|
|Signer|Repo metadata signing|
|PulpContent|Serves content (repos/packages) to edge mirrors|
|NginxContent|Nginx *proxy* that handles TLS termination for PulpContent|
