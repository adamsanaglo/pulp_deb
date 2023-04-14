#!/usr/bin/bash
# Build all the packages-microsoft-prod rpms, debs, and config/list files.
# Requires lintian, rpmbuild, make, and jq to be installed.
# Allows three optional args: type, distro, and release_version, to restrict what is built.
# Otherwise all distros defined in build_targest.json are built.

if [ "$1" == "--help" ]; then
   echo "Usage: ./build.sh [rpm|deb] [<distro>] [<release_version>]"
   echo "Example: ./build.sh"
   echo "Example: ./build.sh rpm rhel 9"
   exit
fi

if [[ -z "$1" || "$1" == "deb" ]]; then
   pushd deb
   ./build.sh "$2" "$3"
   popd
fi
if [[ -z "$1" || "$1" == "rpm" ]]; then
   pushd rpm
   ./build.sh "$2" "$3"
   popd
fi
