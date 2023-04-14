#!/usr/bin/bash
# Build all the packages-microsoft-prod rpms and repo files.
# Requires rpmbuild and jq to be installed.
# Allows two optional args, distro and release_version, to restrict what packages are built.
# Otherwise all distros defined in build_targest.json are built.

define_keys_array () {
  # reads the keys of the object specified in jq query $2 and assigns it to an array named $1
  readarray -t $1 < <(jq "$2 | keys" build_targets.json | tr -d '[],"')
}

read_value () {
  # reads the value specified by the jq query $1
  jq $1 build_targets.json | tr -d '"'
}

define_keys_array distros '.'
if [ ! -z "$1" ]; then
  if [[ ! " ${distros[*]} " =~ " $1 " ]]; then
    echo "ERROR: requested distro $1 is unknown. Distros _must_ be defined in build_targets.json."
    exit 1
  else
    distros=($1)
  fi
fi

for distro in ${distros[@]}; do
  configroot=$(read_value ".${distro}.configroot")
  define_keys_array channels ".${distro}.channels"
  define_keys_array release_versions ".${distro}.release_versions"

  if [ ! -z "$2" ]; then
    if [[ " ${release_versions[*]} " =~ " $2 " ]]; then
      release_versions=($2)
    else
      echo "ERROR: requested release_version $2 is unknown. Release versions _must_ be defined in build_targets.json."
      exit 1
    fi
  fi

  for release_version in ${release_versions[@]}; do
    define_keys_array additional_channels ".${distro}.release_versions.\"${release_version}\".additional_channels"
    rpmbuild --define "_topdir $(pwd)" --define "distro $distro" --define "release_version $release_version" \
             --define "configroot $configroot" --define "_rpmdir $(pwd)/RPMS/$distro/$release_version" \
             packages-microsoft-prod.spec -bb --quiet
    
    for channel in ${channels[@]}; do
      channel_name=$(read_value ".${distro}.channels.\"${channel}\"")
      BUILD/repo_config.sh "SOURCES/repo.template" "RPMS/$distro/$release_version/noarch" "$channel" "$distro" "$release_version" "$channel" "$channel_name"
    done
    
    for channel in ${additional_channels[@]}; do
      channel_name=$(read_value ".${distro}.release_versions.\"${release_version}\".additional_channels.\"${channel}\"")
      BUILD/repo_config.sh "SOURCES/repo.template" "RPMS/$distro/$release_version/noarch" "$channel" "$distro" "$release_version" "$channel" "$channel_name"
    done
  done
done