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

## For Publishers: How to use in Azure Pipeline

*Prerequisite: Your repository's organization must have "Publish Linux Packages (PMC)" installed from Marketplace as a usable task.

1. Use the Azure Key Vault task to download your publisher cert.

2. Find "Publish Linux Packages (PMC)" in your organization's task library and select it.

3. Enter all the information needed in the input fields. For `Publisher Cert`, enter the name of the cert downloaded from KeyVault, formatted as `$(YOUR_SECRETS_FILTER_NAME)`. Then click `Add`.

4. The extension along with its inputs should show up within your `.yaml`. Please be sure to remove the single quotation marks around `$(YOUR_SECRETS_FILTER_NAME)`. If this isn't done, the cert's contents will not be passed into the extension and the build will fail.

5. Set up any other remaining tasks and you should be able to save and run the pipeline.

## For Developers: Setting Up for Use Locally

To run this extension locally, NodeJS, Docker Desktop, and TypeScript must be installed. This repository should also be cloned, as you will need `main.ts` along with the `Dockerfile` in `/Compute-PMC/cli`. Please also make sure to have your publisher cert downloaded somewhere locally as there will be no KeyVault access.

Before running the last step, you must have Docker Desktop running. You should also be connected to MSFTVPN.

A guide for NodeJS (and WSL2 if not already installed): <https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-wsl>

A guide for Docker: <https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers>

After installation, the following must be done:

1. In terminal, navigate to the directory containing the cloned content.

    `cd ~/Compute-PMC/extension-prototype/buildandrelease`

2. Install TypeScript version 4.0.2

    `npm install typescript@4.0.2 -g --save-dev`

3. Install all necessary dependencies.

    `npm i` or `npm install`

4. Run `tsc` in terminal within `buildandrelease` so that a new `main.js` can be generated to use.

5. Create a `.env` file within `buildandrelease` and set the following:

```text
INPUT_PROFILE="ppe"
INPUT_MSAL_CLIENT_ID="YOUR_CLIENT_ID"
INPUT_MSAL_SNIAUTH="no-msal-sniauth"
INPUT_PACKAGE_PATH="YOUR_PACKAGE_DIRECTORY_PATH"
INPUT_REPOSITORY="YOUR_TARGET_REPOSITORY_NAME"
```

6. Load the variables in the .env into the WSL2 environment.

    `export $(xargs < .env)`

7. Load your cert contents into the WSL2 environment.

    `export INPUT_MSAL_CERT=$(cat YOUR_CERT_FILE_PATH)`

8. Run the code

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
