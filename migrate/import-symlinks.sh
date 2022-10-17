#!/bin/bash -e

# Take a symlink dump from vcurrent and create a new distro for each symlink
#
# To get a symlink dump, run these commands on a aptcatalog mirror:
#
# cd /var/www/html
# find . -type l -xtype d -ls | tr -s " " | cut -d " " -f12-14 > ~/symlinks.txt
#

function bail {
    >&2 echo ${@}
    exit 1
}

input="${1}"
root="/var/reporoot/"
pmc="../cli/.venv/bin/pmc"

if  [[ -z "${input}" ]]; then
    bail "Must specify a symlinks filename"
elif [[ ! -f "${input}" ]]; then
    bail "File ${input} does not exist!"
fi

failed=()
count=0

while IFS= read -r line; do
    source=$(echo $line | cut -d " " -f 1 | sed 's#^\./##')
    dest=$(echo $line | cut -d " " -f 3 | sed "s#^$root##")

    if [[ $source == $dest ]]; then
        # skip symlinks like './repos/vscode -> /var/reporoot/repos/vscode'
        continue
    fi

    echo "Processing $source -> $dest"

    if [[ $dest = yumrepos/* ]]; then
        type="yum"
    elif [[ $dest = repos/* ]]; then
        type="apt"
    else
        echo "Could not parse type from $dest"
        failed+=("${source} -> ${dest}")
        continue
    fi

    source_matches=$($pmc distro list --base-path $source)
    if [[ $(echo $source_matches | jq -r ".count") -gt 0 ]]; then
        printf "'$source' already exists. Skipping.\n\n"
        continue
    fi


    # look up the existing distro for the repo id
    dest_matches=$($pmc distro list --base-path $dest)
    if [[ $(echo $dest_matches | jq -r ".count") -lt 1 ]]; then
        echo "Error: could not find existing distro with path '$dest'."
        failed+=("${source} -> ${dest}")
    else
        repo=$(echo $dest_matches | jq -r '.results | first.repository')
        echo "Creating distro with path '$source'."
        if ! $pmc distro create $source $type $source --repository $repo; then
            echo "Failed to create distro for '$source'"
            failed+=("${source} -> ${dest}")
        else
            count=$((count+1))
        fi
    fi

    echo ""
done < $input

echo "Created $count distros with ${#failed[@]} failures."
for val in "${failed[@]}"; do
    echo "Failed symlink: $val"
done
