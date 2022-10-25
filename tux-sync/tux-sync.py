#!/usr/bin/python3
from keyvault_util import keyvault_util
from pathlib import Path

import requests
import time
import sys
import util

kv_util = None
msi_client_id = "eaa61057-9a02-4522-a5cf-0a2bc427a0ae"
akv = "pmc-tux-keyvault-51689"
root_folder="/var/lib/pmc"

# ACR Details
acr="pmctuxacr.azurecr.io"
acr_username = "55391a9d-3c3b-4e4a-afa6-0e49c2245175"
acr_secret_name = "ingest-acr"
acr_images = [
    "pmcserver_api",
    "pulp",
    "signer"
]

# Azure Function
af_secret_name = "afQueueActionUrl"

# Cotnainer Secrets
secret_paths = {
    "pmcserver_api": [
        "pmcPostgresPassword",
        "pulpAdminPassword",
        "pulpPostgresPassword"
    ],
    "pulp": [
        "pulpAdminPassword",
        "pulpBlobStorageKey",
        "pulpPostgresPassword",
        "pulpSecret",
        "pulpSymmetricKey"
    ],
    "signer": [
        "legacy-sign",
        "esrp-auth-tux"
    ],
    "nginx": [
        "API-TLS"
    ],
    "nginx-conf": []
}

def get_kv_util():
    """
    Maintain a single instance of keyvault_util
    """
    global kv_util
    if kv_util is not None:
        return kv_util
    print("Creating keyvault_util instance")
    kv_util = keyvault_util(client_id = msi_client_id)
    return kv_util

def create_directories():
    """
    Ensure directories exist so secrets can be written there
    """
    cmd="sudo install -o root -g root -m 700 -d"
    util.run_cmd(f"{cmd} {root_folder}")

    for path in secret_paths:
        new_folder = Path(root_folder) / path
        util.run_cmd(f"{cmd} {new_folder}")


def fetch_secrets():
    """
    Fetch secrets to {root_folder}
    """
    kvutil = get_kv_util()
    for path, secret_list in secret_paths.items():
        for secret_name in secret_list:
            secret_value = kvutil.get_secret(akv, secret_name)
            dest_file = f"{root_folder}/{path}/{secret_name}"
            with open(f"{dest_file}", "w") as f:
                f.write(secret_value)
            print(f"Wrote {secret_name} to {dest_file}")


def fetch_docker_images():
    """
    Fetch images from ACR
    """
    kvutil = get_kv_util()
    acr_secret = kvutil.get_secret(akv, acr_secret_name)
    util.run_cmd(f"sudo docker login -u {acr_username} -p {acr_secret} {acr}")
    for image in acr_images:
        print(f"Fetching {acr}/{image}")
        util.run_cmd(f"sudo docker pull {acr}/{image}")


def install_nginx_config():
    """
    Copy nginx config into mountable folder
    """
    nginx_dir = Path(root_folder) / "nginx-conf"
    util.run_cmd(f"sudo cp nginx/ssl.conf {nginx_dir}")


def update_function_url():
    """
    Insert the AF_QUEUE_ACTION_URL into the env file
    """
    kvutil = get_kv_util()
    af_queue_url = kvutil.get_secret(akv, af_secret_name)
    var_name="AF_QUEUE_ACTION_URL"
    cmd = f"sed -i s|^{var_name}=.*|{var_name}={af_queue_url}| .env-api"
    util.run_cmd(cmd)

def restart_containers():
    docker_compose_cmd = "sudo docker compose"
    for param in ["down", "up -d"]:
        print(f"Running {docker_compose_cmd} {param}")
        util.run_cmd(f"{docker_compose_cmd} {param}")

def smoke_test():
    print("Waiting for containers to come online...")
    time.sleep(3)
    try:
        res = requests.get("http://127.0.0.1:8000/api/")
        status = f"[{res.status_code}]: {res.text}"
        ok = res.ok
    except Exception as e:
        status = str(e)
        ok = False
    if not ok:
        print(f"FAILURE: {status}")
        sys.exit(1)
    print(f"SUCCESS: {status}")


# Make Directories (if not present)
create_directories()

# Fetch Secrets
fetch_secrets()

# Fetch Docker Images
fetch_docker_images()

# Copy nginx config into place
install_nginx_config()

# Update Function Url
update_function_url()

# Restart containers
restart_containers()

# Test API Container
smoke_test()
