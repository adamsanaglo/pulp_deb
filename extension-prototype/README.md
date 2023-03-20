---
Language: TypeScript
---

# PMC Linux Package Publishing Helper

The Linux Package Publishing Helper is designed as an Azure DevOps (ADO) extension that helps publishers avoid the scaffolding work associated with using the PMC cli. There is also a way to run this helper without ADO. More on this later.

Prior to the development of this tool, publishers had to manually install the cli either in their ADO Pipeline or onto their local OS terminal, create their own settings.toml / .json to satisfy the cli's configuration requirements, then finally learn all the pmc commands needed to fully publish a package or file.

With this tool, publishers no longer need to do all of that. The following configuration options are all that any publisher will need to pick or pass in:

- profile
- msal client ID
- msal cert path (local from root)
- msal SNIAuth
- package path (local from root)
- repository name in PMC

## For Developers: Setting Up for Use Locally

*This is for pre-image upload. Instructions will be updated once the image is hosted on MCR. A comprehensive page of instructions can be found here: <https://learn.microsoft.com/en-us/azure/devops/extend/develop/add-build-task?toc=%2Fazure%2Fdevops%2Fmarketplace-extensibility%2Ftoc.json&view=azure-devops>

To run this extension locally, NodeJS, Docker Desktop, and TypeScript must be installed. This repository should also be cloned, as you will need `main.ts` along with the `Dockerfile` in `/Compute-PMC/cli`.

A guide for NodeJS (and WSL2 if not already installed): <https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-wsl>

A guide for Docker: <https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers>

After installation, the following must be done:

1. In terminal, navigate to the directory containing the cloned content.

    `cd ~/Compute-PMC/extension-prototype/buildandrelease`

2. Install TypeScript version 4.0.2

    `npm install typescript@4.0.2 -g --save-dev`

3. Install all necessary dependencies.

    `npm i` or `npm install`

4. Build the Docker image from the Dockerfile

    `docker build -t extension-image ~/Compute-PMC/cli`

5. Create a `.env` file within `buildandrelease` and set the following:

```text
INPUT_PROFILE="ppe"
INPUT_MSAL_CLIENT_ID="YOURCLIENTID"
INPUT_MSAL_CERT_PATH="YOURCERTPATH"
INPUT_MSAL_SNIAUTH="no-msal-sniauth"
INPUT_PACKAGE_PATH="YOURPACKAGEPATH"
INPUT_REPOSITORY="YOURTARGETREPOSITORY"
```

1. Load the variables in the .env into the WSL2 environment.

    `export $(xargs < .env)`

2. Run the code

    `node main.js`

If the core code in `main.ts` must be changed at any point, you must call `tsc` in terminal while inside `buildandrelease` in order for a new `main.js` to compile.

## For developers: Building the `.vsix` File

*Note: Node must be installed.

1. Install the Cross-Platform CLI for Azure DevOps through the WSL2 terminal.

    `npm i -g tfx-cli`

2. In terminal, navigate to the root directory of the extension (where `vss-extension.json`) lives.

    `cd ~/Compute-PMC/extension-prototype`

3. Package the extension.

    `tfx extension create --manifest-globs vss-extension.json`

After the third step, a new `.visx` extension should be generated in the root directory of the extension. This is the file that will need to be uploaded into ADO whenever any changes have been made to `main.ts` in the `buildandrelease` directory. You may also want to change the version number within `vss-extension.json` to reflect the iteration of the extension. In addition, please ensure that your most recent `main.ts` is compiled into `main.js` before building the extension to avoid any issues. It is the JavaScript code that is the engine behind that `.vsix` file.
