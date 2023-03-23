FROM mcr.microsoft.com/cbl-mariner/base/python:3.9

ENV PIP_ROOT_USER_ACTION=ignore

# set PIP_INDEX_URL to an Azure Artifacts feed URL
# e.g. docker build --build-arg "PIP_INDEX_URL=https://a:XXX@msazure.pkgs.visualstudio.com/_packaging/Compute-PMC/pypi/simple/" ...
ARG PIP_INDEX_URL
RUN test -n "$PIP_INDEX_URL" || (echo "PIP_INDEX_URL not set. Exiting." && false)

RUN pip install --upgrade pip

COPY . cli

RUN pip install ./cli

ENTRYPOINT ["pmc"]
