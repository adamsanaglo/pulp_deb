#!/usr/bin/bash
# Build all the packages-microsoft-prod debs and list files.
# Requires lintian, make, and jq to be installed.
# Allows two optional args, distro and release_version, to restrict what packages are built.
# Otherwise all distros defined in build_targest.json are built.

define_array () {
  # reads the array specified in jq query $2 and assigns it to an array named $1
  readarray -t $1 < <(jq "$2" build_targets.json | tr -d '[],"')
}

read_value () {
  # reads the value specified by the jq query $1
  jq $1 build_targets.json | tr -d '"'
}

configure_list () {
  # copy and configure the list file.
  # expects args: <destination> <distro> <release_version> <repo> <dist>
  cp SOURCES/list.template $1
  sed -i "s/DISTRO/$2/g" $1
  sed -i "s/RELVER/$3/g" $1
  sed -i "s/REPO/$4/g" $1
  sed -i "s/DISTRIBUTION/$5/g" $1
}

define_array distros '. | keys'
if [ -z "$1" ]; then
  echo "Building all distros: ${distros[@]}"
elif [[ ! " ${distros[*]} " =~ " $1 " ]]; then
  echo "ERROR: requested distro $1 is unknown. Distros _must_ be defined in build_targets.json."
  exit 1
else
  distros=($1)
fi

for distro in ${distros[@]}; do
  define_array release_versions ".${distro}.release_versions | keys"
  define_array channels ".${distro}.channels"
  if [ ! -z "$2" ]; then
    if [[ " ${release_versions[*]} " =~ " $2 " ]]; then
      release_versions=($2)
    else
      echo "ERROR: requested release_version $2 is unknown. Release versions and aliases _must_ be defined in build_targets.json."
      exit 1
    fi
  fi
  for release_version in ${release_versions[@]}; do
    release_alias=$(read_value ".${distro}.release_versions.\"${release_version}\".alias")
    define_array additional_channels ".${distro}.release_versions.\"${release_version}\".additional_channels"
    dest_dir="DEBS/$distro/$release_version"
    mkdir -p $dest_dir
    configure_list SOURCES/microsoft-prod.list "$distro" "$release_version" prod "$release_alias"
    make DISTRO=$distro RELVER=$release_version
    rm SOURCES/microsoft-prod.list
    mv *.deb $dest_dir
    make clean

    for channel in ${channels[@]}; do
      # These go in the prod repo but in a different distribution.
      configure_list $dest_dir/$channel.list "$distro" "$release_version" prod "$channel"
    done
    for channel in ${additional_channels[@]}; do
      # These go in separate repos with the release alias as the distribution.
      configure_list $dest_dir/$channel.list "$distro" "$release_version" "$channel" "$release_alias"
    done
  done
done