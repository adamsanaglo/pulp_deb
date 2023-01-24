# MUST use azure-cli 2.20 because the xsign extension only works with that version
# https://github.com/microsoft/Sign.Client.AzCli/issues/2

# MUST use python 3.9, because collections.iterable is unsupported in 3.10,
# which causes an error installing the xsign extension.
# https://github.com/microsoft/Sign.Client.AzCli/issues/3
FROM mcr.microsoft.com/cbl-mariner/base/python:3.9
RUN tdnf install -y openssl-devel python3-pip redis

RUN pip install --upgrade pip && \
    pip install setuptools==57.5 retrying fastapi[all] redis azure-keyvault-secrets azure-identity pydantic[dotenv] asgi-correlation-id==3.1.0 && \
    pip install azure-cli==2.20.0

COPY . /signer
RUN az extension add -y -s /signer/xsignextension-0.31-py2.py3-none-any.whl && \
    rm -f /signer/xsignextension-0.31-py2.py3-none-any.whl

WORKDIR /signer
EXPOSE 8888
ENTRYPOINT ["/signer/entrypoint.sh"]
