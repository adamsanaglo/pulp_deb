/*
* main.ts
* 
* Will be compiled into javascript and executed when the Publishing Helper is called.
* Capable of publishing packages.
*/

/* -------------------------------------------------------------------------- */
/*                 Required Packages and Helper Functions                     */
/* -------------------------------------------------------------------------- */

import tl = require('azure-pipelines-task-lib/task');
const { execSync } = require('child_process');

interface iProfileOptions {
    [key: string]: string[]
}

interface iResponseItem {
    id: string
}

function generateConfigs(
    profile: string | undefined,
    msal_client_id: string | undefined,
    msal_cert_path: string | undefined,
    msal_SNIAuth: string | undefined) {

    const profileOptions: iProfileOptions = {
        "base-url": [
            "https://tux-ingest.corp.microsoft.com/api/v4",
            "https://pmc-ingest.trafficmanager.net/api/v4",
            "https://ppe-ingest.trafficmanager.net/api/v4"
        ],
        "msal-scope": [
            "api://55391a9d-3c3b-4e4a-afa6-0e49c2245175/.default",
            "api://d48bb382-20ec-41b9-a0ea-07758a21ccd0/.default",
            "api://1ce02e3e-1bf3-4d28-8cdc-e921f824399d/.default"
        ],
        "msal-authority": [
            "https://login.microsoftonline.com/Microsoft.onmicrosoft.com",
            "https://login.microsoftonline.com/MSAzureCloud.onmicrosoft.com",
            "https://login.microsoftonline.com/Microsoft.onmicrosoft.com"
        ]
    }

    let toggle: number | undefined;
    switch (profile) {
        case "tuxdev":
            toggle = 0;
            break;
        case "ppe":
            toggle = 2;
            break;
        default:
            toggle = 1;
            break;
    }

    let options: string = '';
    for (const key in profileOptions) {
        options += `--${key} ${profileOptions[key][toggle]} `
    }

    options += `--msal-client-id ${msal_client_id} `;
    options += `--msal-cert-path ${msal_cert_path} `;
    options += `--${msal_SNIAuth}`;
    return options;
}

function getPackageID(packageIDCommand: string | undefined) {
    let response: Array<iResponseItem> | undefined;
    let parsedIDs: Array<string> = new Array();

    try {
        response = JSON.parse(execSync(packageIDCommand).toString());
        if (response != undefined) {
            for (const item of response) {
                parsedIDs.push(item.id);
            }
        }
    } catch (e: any) {
        tl.setResult(tl.TaskResult.Failed, `Operation failed: ${e.stdout}`);
    }

    return parsedIDs.join();
}

function updateOrPublish(runCommand: string | undefined) {
    let execSuccess: boolean = true;
    let OperationOuput: string | undefined;

    try{
        OperationOuput = execSync(runCommand).toString();
        console.log(`Operation succeeded: ${OperationOuput}`);
    } catch (e: any) {
        execSuccess = false;
        tl.setResult(tl.TaskResult.Failed, `Operation failed: ${e.stdout}`);
    }

    return execSuccess;
}

function repositoryCheck(repository: string | undefined) {
    if (repository == undefined) {
        return false;
    }

    const repoType = ['yum', 'apt', 'file'];
    const repoTypeSuffix: string | undefined = repository?.slice(repository?.lastIndexOf('-') + 1);

    return repoType.includes(repoTypeSuffix);
}

function inputCheck(
    sourceDir: string | undefined,
    profile: string | undefined,
    msal_client_id: string | undefined,
    msal_cert_path: string | undefined,
    msal_SNIAuth: string | undefined,
    repository: string | undefined) {

    if (sourceDir == undefined) {
        tl.setResult(tl.TaskResult.Failed, 'Need source directory path');
        return;
    } else if (profile == undefined) {
        tl.setResult(tl.TaskResult.Failed, 'Profile needs to be specified');
        return;
    } else if (msal_client_id == undefined) {
        tl.setResult(tl.TaskResult.Failed, 'Need client ID');
        return;
    } else if (msal_cert_path == undefined) {
        tl.setResult(tl.TaskResult.Failed, 'Need cert path');
        return;
    } else if (msal_SNIAuth == undefined) {
        tl.setResult(tl.TaskResult.Failed, 'Must indicate whether Subject Name Issuer Auth should be used')
        return;
    } else if (!repositoryCheck(repository)) {
        tl.setResult(tl.TaskResult.Failed, 'Repository name must be entered with the appropriate type suffix')
    }
}

/* -------------------------------------------------------------------------- */
/*                          Main Executing Function                           */
/* -------------------------------------------------------------------------- */

function main() {
    try {
        // Retrieve user inputs
        const sourceDir: string | undefined = tl.getPathInput('package_path', false, false);
        const profile: string | undefined = tl.getInput('profile', true);
        const msal_client_id: string | undefined = tl.getInput('msal_client_id', true);
        const msal_cert_path: string | undefined = tl.getPathInput('msal_cert_path', false, false);
        const msal_SNIAuth: string | undefined = tl.getInput('msal_SNIAuth', true);
        const repository: string | undefined = tl.getInput('repository', true);

        // Checks that all inputs are present
        inputCheck(sourceDir, profile, msal_client_id, msal_cert_path, msal_SNIAuth, repository);

        const dockerImage = 'mcr.microsoft.com/unlisted/pmc/pmc-cli';

        const dockerCommand: string = `docker run -v ${msal_cert_path}:${msal_cert_path} -v ${sourceDir}:${sourceDir} ${dockerImage}`;
        const cliOptions: string = generateConfigs(profile, msal_client_id, msal_cert_path, msal_SNIAuth);
        // const typeOption: string = sourceDir?.slice(sourceDir.lastIndexOf('.') + 1) == 'txt' ? ' --type file' : '';
        
        // Build command to retrieve a package ID for the package to upload
        const packageIDCommand: string = `${dockerCommand} ${cliOptions} package upload ${sourceDir}`;
        const packageIDs = getPackageID(packageIDCommand);

        // Build command to update the repo with the package
        const updateRepoPackageCommand: string = `${dockerCommand} ${cliOptions} repo packages update ${repository} --add-packages ${packageIDs}`;
        updateOrPublish(updateRepoPackageCommand);

        // Build command to publish the repo
        const publishRepoCommand: string = `${dockerCommand} ${cliOptions} repo publish ${repository}`;
        updateOrPublish(publishRepoCommand);
    }
    catch (err: any) {
        tl.setResult(tl.TaskResult.Failed, err.message);
    }
}

main();