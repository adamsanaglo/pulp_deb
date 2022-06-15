#!/bin/bash -e
# A simple script to get a dev environment running

function enableDockerRepos() {
    # Enable Docker package repository
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
}

function installDockerEngine() {
    # Used primarily with Ubuntu Server
    # Fetch docker engine
    sudo apt update -qq
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
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

function prerequisites() {
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg lsb-release make httpie
}

function startServer() {
    sudo make run
}

prerequisites
make .env
enableDockerRepos
# installDockerDesktop
installDockerEngine
startServer
