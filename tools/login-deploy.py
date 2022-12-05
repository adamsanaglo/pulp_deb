#!/usr/bin/python3
# Uses MSI to login to an AME Service Principal via az cli
# This is done prior to running update.sh in prod
import subprocess
import sys
import tempfile

from keyvault_util import keyvault_util

msi_client_id = "a9c6a416-1940-403e-9935-0fe791760491"
sp_app_id = "726fc884-730c-4082-8686-8ba0a3ebd203"
aad_tenant = "33e01921-4d64-4f8c-a055-5bdaffd5e33d"
akv = "pmcprod"
cert_name = "deploy"

# Login to AKV and download cert to a temporary file
print("Retrieving secret from AKV")
kv_util = keyvault_util(client_id=msi_client_id)
cert_file = tempfile.NamedTemporaryFile(suffix="pem", delete=False)
cert_value = kv_util.get_secret(akv, cert_name)
with open(cert_file.name, "w") as f:
    f.write(cert_value)
print(f"Cert written to {cert_file.name}. Remove it when done :)")
# TODO: Remove the cert via .bash_logout. Az CLI needs it for the duration of the session

# Login to az cli, then delete the cert from disk
print("Logging into az cli")
cmd = "az login --use-cert-sn-issuer --service-principal"
cmd += f" -u {sp_app_id} -p {cert_file.name} -t {aad_tenant}"
try:
    res = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res.stdout = res.stdout.decode("utf-8", "replace")
    res.stderr = res.stderr.decode("utf-8", "replace")
except Exception as e:
    print(e)
    sys.exit(1)

if res.returncode != 0:
    print(res.stderr)
    sys.exit(1)
print(res.stdout)
