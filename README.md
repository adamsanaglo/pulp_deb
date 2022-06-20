---
Language: python
---

# PMC (package.microsoft.com) Server and Client

The ultimate intent of this project is to provide teams inside Microsoft an easy and scalable
way to publish their linux packages.
To do that we're using Pulp to manage the packages and repositories and relying on Azure Container
Registry (ACR) for worldwide scalable distribution.
We are also creating a thin Server and Client Tool that stand in front of Pulp to add
needed authentication and functionality that Pulp does not natively support.

A simple architectural diagram of the desired end-state would look something like this:

<pre>
PMC-Client <- - - v
                  |- -> PMC-Server <- - -> Pulp <- - -> ACR <- - -> packages.microsoft.com
Direct HTTP  <- - ^         ^
                            |
                            v
                       PMC-Database
</pre>

The code for PMC-Client and PMC-Server lives here, and the dev workstation setup runs containers
for the DB and Pulp.

## Developing

The [Client](cli/README.md) and [Server](server/README.md) pieces currently have their own docs
and setup, so see them for more info.

## IDE Setup

### Visual Studio Code

Here's an example VS Code settings file with some useful stuff in it, which can be found by
Ctrl-Shift-P and searching for "Preferences: Open Workspace Settings (JSON)"

<!-- language: json -->

    {
        "editor.formatOnSave": true,
        "python.formatting.provider": "black",
        "python.testing.cwd": "./cli",
        "python.formatting.blackArgs": [
            "--line-length",
            "100"
        ],
        "editor.rulers": [
            100
        ]
    }
