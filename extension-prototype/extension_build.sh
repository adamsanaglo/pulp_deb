#!/bin/bash
echo "Entering directory"
scriptdir="$(dirname ${BASH_SOURCE[0]})"
cd ${scriptdir}/buildandrelease
echo "Installing TypeScript"
npm install typescript@4.6.3 -g --save-dev
echo "Installing Tfx-CLI"
npm install -g tfx-cli
echo "Install all remaining dependencies"
npm install
echo "Generate main.js"
tsc
echo "Returning to root directory"
cd ..
echo "Packaging the extension"
if [[ -n "${1}" ]]; then
    outdir="${1}"
else
    echo "No output parameter specified. Will write extension to ${scriptdir}"
    outdir="${scriptdir}"
fi
tfx extension create --manifest-globs vss-extension.json --output-path "${outdir}"