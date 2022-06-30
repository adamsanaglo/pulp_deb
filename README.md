---
Language: python
---

# PMC (packages.microsoft.com) Server and Client

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

### black

We use black to format our code. black integrates with a number of IDEs. For more info see:

https://black.readthedocs.io/en/stable/integrations/editors.html

### Visual Studio Code

First, you will need to install a couple of extensions. If you are running PMC inside WSL, make sure
you have the 'Remote - WSL' extension installed. Also, we recommend installing the isort extension
from Microsoft.

Here's an example VS Code settings file with some useful stuff in it, which can be found by
Ctrl-Shift-P and searching for "Preferences: Open Workspace Settings (JSON)". You may need to tailor
the paths depending on where you store your workspace file.

<!-- language: json -->

    {
        "folders": [
            {
                "path": "Compute-PMC\\server"
            },
            {
                "path": "Compute-PMC\\cli"
            }
        ],
        "settings": {
            "editor.formatOnSave": true,
            "editor.codeActionsOnSave": {
                "source.organizeImports": true
            },
            "python.linting.flake8Enabled": true,
            "python.linting.mypyEnabled": true,
            "python.formatting.provider": "black",
            "python.formatting.blackArgs": [
                "--line-length",
                "100"
            ],
            "editor.rulers": [
                100
            ],
            "isort.args": [
                "--profile",
                "black",
                "--line-length",
                "100"
            ],
        }
    }


### vim/neovim

There are some plugins that provide linting/code formatting to vim (e.g. black has [its own vim
plugin](https://github.com/psf/black/blob/main/plugin/black.vim)) but I recommend using [ALE
(Asynchronous Lint Engine)](https://github.com/dense-analysis/ale) which handles a variety of code
linters and formatters. ALE also works with both vim and neovim.

#### ALE

See ALE's installation guide for how to install ALE: https://github.com/dense-analysis/ale#installation

To configure ALE for our project, add this to your rc file:

```
let g:ale_fixers = {"python": ["black", "isort"]}
```

It should pick up our project's settings in pyproject.toml.

Optionally, you can have ALE format on save:

```
let g:ale_fix_on_save = 1
```

Alternatively, you can create a keyboard binding to run ALEFix:

```
map <Leader>f :ALEFix<CR>
```
