# Packages.microsoft.com (PMC) vNext Preview

Thanks for participating in our preview of the vNext API! Since the start of 2022 we've been hard at work building a new package publishing experience that should remove many of the "sharp edges" in the current infrastructure, while enabling support for some new scenarios. Your feedback will be very valuable in shaping the service as we approach GA. This preview (and document) is scoped to the tux-dev environment (tux-devrepo.corp.microsoft.com).

## Prerequisites

### **Service Principal**

If you already have a Service Principal for publishing to tux-dev, it should still work in the new environment.
If you don't have a Service Principal, you can create one as described [here](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal).

- If you don't currently have an account for tux-dev, or if your existing account doesn't work, you can request assistance [here](https://forms.office.com/r/15vCGkK59V).
- NOTE: Only Certificate Auth is supported.

### **Corpnet Access**

Tux-dev is only accessible from Corpnet.

### **PMC CLI**

The new CLI is a platform-agnostic Python package which can be installed from tux-dev.

```bash
pip install http://tux-devrepo.corp.microsoft.com/pypi/pmc_cli-0.0.2-py3-none-any.whl
```

### **Client Config**

Your config should reside at `~/.config/pmc/settings.toml`. Use the sample below and fill in your Service Principal **Client ID** and the **path to your cert**.

```ini
[cli]
no_wait = false
no_color = false
id_only = false
format = "json"
debug = false
base_url = "https://tux-ingest.corp.microsoft.com/api/v4"
msal_client_id = "YOUR_CLIENT_ID"
msal_scope = "api://55391a9d-3c3b-4e4a-afa6-0e49c2245175/.default"
msal_cert_path = "/PATH/TO/YOUR/CERT"
msal_SNIAuth = true
msal_authority = "https://login.microsoftonline.com/Microsoft.onmicrosoft.com"
```

## PMC Client

References for using the new PMC client are located [here](../pmctool/index.md)
