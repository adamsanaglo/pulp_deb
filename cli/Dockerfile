FROM mcr.microsoft.com/cbl-mariner/base/python:3.9

RUN pip install --upgrade pip

# Copied from pyproject.toml
# TODO: onboard packages.microsoft.com as a trusted source and switch back to using
# --extra-index-url when installing pmc-cli
# https://msazure.visualstudio.com/One/_workitems/edit/17458870
RUN pip install "typer~=0.6.1" \
                "httpx~=0.23.0" \
                "pydantic~=1.10.2" \
                "tomli-w~=1.0.0" \
                "msal~=1.19.0" \
                "pyOpenSSL~=22.1.0" \
                "tomli~=2.0.1"
# END TODO

RUN pip install --index-url https://packages.microsoft.com/pmc-cli/simple/ "pmc-cli>=0.1.0"

ENTRYPOINT ["pmc"]
