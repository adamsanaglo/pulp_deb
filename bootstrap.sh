#!/bin/bash -e
# A simple script to get a dev environment running

OS=$(awk -F= '/^NAME/{print $2}' /etc/os-release | tr -d '"')

function installDebDocker() {
    # Enable Docker package repository
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # install docker packages
    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

function installDockerDesktop() {
    # Used primarily with WSL
    # Install prereqs
    sudo apt update -qq
    sudo apt install -y wget docker-ce-cli qemu-system-x86 pass desktop-file-utils \
      libgtk-3-0 libx11-xcb1 uidmap

    # Install Docker Desktop (site license)
    # Not available via repo, must download deb
    dockerPkg=docker-desktop-4.9.0-amd64.deb
    checksum=162595a35962c8478f22a067b584ad420a2b42cbf453ad9d423d5bfb3d9308c2
    wget https://desktop.docker.com/linux/main/amd64/${dockerPkg}
    echo "${checksum}  ${dockerPkg}" | sha256sum -c
    sudo dpkg -i ./${dockerPkg}
    rm -f ${dockerPkg}
}

function installDebs() {
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg lsb-release make httpie python3-venv python3-pip
}

function setupPoetry() {
    pip install pipx
    python -m pipx ensurepath

    pipx install poetry
    poetry config virtualenvs.in-project true
}

function setupCli() {
    pushd cli
    make tests/settings.toml
    poetry install
    pip install pygments  # color output
    popd
}

function setupServer() {
    pushd server
    poetry install  # install deps locally so IDEs can have access to type stubs, etc
    popd
}

if [[ $OS == "Ubuntu" ]]; then
    installDebs

    if ! [ -x "$(command -v docker)" ]; then
        # installDockerDesktop
        installDebDocker
    else
        echo "Docker already installed. Skipping."
    fi
fi

setupPoetry
setupCli
setupServer

echo "Now cd into the server directory and run 'make run' to run the pmc server."
