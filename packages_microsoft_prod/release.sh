#!/usr/bin/bash
# For each distribution_version:
# 0. If $1 == --dev create the microsoft-*-prod target repo / dist if it does not already exist.
# 1. Create the config repo / dist if it does not already exist
# 2. Upload the files for it.
# 3. Add the files to the repo.
# 4. Add rpms/debs to the target repo.
# 5. Create a "user-friendly" dist for the target repo.
# 6. Publish the target repo.
# 7. Publish the config repo.

REPO_ADMIN_PROFILE_NAME=${REPO_ADMIN_PROFILE_NAME:-"repo"}
PACKAGE_ADMIN_PROFILE_NAME=${PACKAGE_ADMIN_PROFILE_NAME:-"package"}

current_profile=$REPO_ADMIN_PROFILE_NAME

pmc () {
    poetry --directory ../cli run pmc --profile $current_profile "$@"
}

define_array () {
  # reads the array specified in jq query $2 and assigns it to an array named $1
  readarray -t $1 < <(jq "$2" $3 | tr -d '[],"')
}

comma_separated () {
  # returns a comma-sparated string representation of the args
  arr=("$@")
  delim=""
  joined=""
  for item in "${arr[@]}"; do
    joined="$joined$delim$item"
    delim=","
  done
  echo $joined
}

ensure_symlink_distro () {
  # $1 = name of the target repo, $2 = path of the symlink dist, $3 = repo type
  symlink_target_id=$(pmc --id-only repo list --name $1)
  if [[ ! "$symlink_target_id" =~ repositories.* ]]; then
    echo "ERROR: could not find expected repo: $1"
    return
  fi

  distro_id=$(pmc --id-only distro list --base-path $2)
  if [[ ! "$distro_id" =~ distributions.* ]]; then
    distro_id=$(pmc --id-only distro create $2 $3 $2 --repository $symlink_target_id)
  fi
}

for dir in "deb/DEBS" "rpm/RPMS"; do
  if [ "$dir" == "deb/DEBS" ]; then
    type="apt"
    extension="deb"
    path_prefix="repos"
  else
    type="yum"
    extension="rpm"
    path_prefix="yumrepos"
  fi

  for distro in $(ls $dir); do
    define_array channels ".$distro.channels | keys" $extension/build_targets.json
    for full_dir in $dir/$distro/*; do
      version=$(basename $full_dir)
      define_array additional_channels ".$distro.release_versions.\"$version\".additional_channels | keys" $extension/build_targets.json
      if [ "$type" == "apt" ]; then
        alias=$(jq ".${distro}.release_versions.\"${version}\".alias" deb/build_targets.json | tr -d '"')
        target_name_prefix="microsoft-$distro-$alias"
        repo_package_release_arg="$alias"
        base_symlink_distros=(prod)
        additional_channel_suffix="$alias"
      else # yum
        alias=$version
        target_name_prefix="microsoft-$distro$version"
        repo_package_release_arg=""
        base_symlink_distros=(testing ${channels[@]})
        additional_channel_suffix="$distro$version"
        # For RHEL in particular we have some issues with versioning. The prod/insiders/etc repos
        # are always *-rhelX.0-*, and the mssql-server repos are always *-rhelX (without the ".0").
        # Additionally we mistakenly configured the config repo / symlinks for RHEL 9 to be "9.0"
        # when it should have just been "9", which throws off assumptions about which direction to
        # adjust in if you're not careful. Hardcode some fixes.
        if [[ "$distro" = "rhel" && "$version" =~ ^[[:digit:]]+$ ]]; then
          # Add the ".0" to the prod/insiders/etc channel names.
          target_name_prefix="$target_name_prefix.0"
        elif [[ "$distro" = "rhel" && "$version" =~ ^[[:digit:]]+.0$ ]]; then
          # Strip the ".0" from the additional channel suffix (mssql, etc).
          additional_channel_suffix="$distro$(echo $version | sed 's/\([[:digit:]]\+\).0/\1/')"
        fi
      fi

      # 0. If $1 == --dev create the microsoft-*-prod target repo / dist if it does not already exist.
      if [ "$1" == "--dev" ]; then
        if [ "$type" == "apt" ]; then
          joined=$(comma_separated nightly testing ${channels[@]})
          releases="${joined/prod/$alias}"  # substitues $alias for "prod"
          pmc repo create $target_name_prefix-prod-apt apt --paths "repos/$target_name_prefix-prod" --releases $releases
        else
          for subrepo in nightly testing ${channels[@]}; do
            pmc repo create $target_name_prefix-$subrepo-yum yum --paths "yumrepos/$target_name_prefix-$subrepo"
          done
        fi
        for channel in ${additional_channels[@]}; do
          pmc repo create $channel-$additional_channel_suffix-$type $type --paths "$path_prefix/$channel-$additional_channel_suffix"
        done
      fi

      target_id=$(pmc --id-only repo list --name $target_name_prefix-prod-$type)
      if [[ ! "$target_id" =~ repositories.* ]]; then
        # If the target repo has not been created yet, there's nothing to do for it. Skip.
        continue
      fi

      # 1. Create the config repo / dist if it does not already exist
      config_name="${distro}_${version}-file"
      config_id=$(pmc --id-only repo list --name $config_name)
      if [[ ! "$config_id" =~ repositories.* ]]; then
        config_id=$(pmc --id-only repo create $config_name file --paths "config/$distro/$version")
      fi

      # 2. Upload the files for it.
      if [ "$1" == "--dev" ]; then
        ../cli/update_role.sh Package_Admin;
        upload_suffix="--ignore-signature"
      else
        upload_suffix=""
        current_profile=$PACKAGE_ADMIN_PROFILE_NAME
      fi
      package=$(ls $full_dir/packages-microsoft-prod*)
      file_ids=$(pmc --id-only package upload --type file $full_dir)
      package_id=$(pmc --id-only package upload $package $upload_suffix)
      if [ "$1" == "--dev" ]; then
        ../cli/update_role.sh Repo_Admin;
      else
        current_profile=$REPO_ADMIN_PROFILE_NAME
      fi

      # 3. Add the files to the repo.
      pmc repo packages update $config_id --add-packages $file_ids

      # 4. Add rpm/deb to the target repo.
      pmc repo packages update $target_id $repo_package_release_arg --add-packages $package_id

      # 5. Create the "user-friendly" dists for the target repo.
      for channel in ${base_symlink_distros[@]}; do
        path=$distro/$version/$channel
        ensure_symlink_distro $target_name_prefix-$channel-$type $path $type
      done
      for channel in ${additional_channels[@]}; do
        path=$distro/$version/$channel
        ensure_symlink_distro $channel-$additional_channel_suffix-$type $path $type
      done

      # 6. Publish the target repo.
      # TODO: revisit. This is dangerous if the publisher is queueing unpublished changes. Maybe
      # we should just let the config package get published along with the next regularly-scheduled
      # batch of changes?
      #pmc --no-wait repo publish $taget_id

      # 7. Publish the config repo.
      pmc --no-wait repo publish $config_id
    done
  done
done
