# MUST use azure-cli 2.20 because the xsign extension only works with that version
# https://github.com/microsoft/Sign.Client.AzCli/issues/2

# MUST use python 3.9, because collections.iterable is unsupported in 3.10,
# which causes an error installing the xsign extension.
# https://github.com/microsoft/Sign.Client.AzCli/issues/3
FROM mcr.microsoft.com/mirror/docker/library/python:3.9-slim
ENV DEBIAN_FRONTEND=noninteractive
COPY . /signer
RUN apt-get update && \
    apt-get install -y cmake curl libssl-dev python3-pip redis supervisor && \
    curl -s https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg && \
    mkdir -p /var/log/supervisor && \
    pip install --upgrade pip && \
    pip install setuptools==57.5 retrying fastapi[all] redis azure-keyvault-secrets azure-identity pydantic[dotenv] && \
    pip install azure-cli==2.20.0 && \
    az extension add -y -s /signer/xsignextension-0.31-py2.py3-none-any.whl && \
    rm -f /signer/xsignextension-0.31-py2.py3-none-any.whl && \
    mv /signer/supervisord.conf /etc/supervisor/conf.d

WORKDIR /signer
EXPOSE 8888
CMD ["/usr/bin/supervisord"]
