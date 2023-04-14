#!/usr/bin/bash
# Copies the repo file template and does some substitutions.
# Usage: repo_config.sh <template_file> <dest_dir> <dest_filename> <distro> <version> <channel> <channel_name>

desired_filename="$2/$3.repo"
cp $1 $desired_filename
sed -i "s@DISTRO@$4@g" $desired_filename
sed -i "s@VERSION@$5@g" $desired_filename
sed -i "s@CHANNEL@$6@g" $desired_filename
sed -i "s@CNAME@$7@g" $desired_filename
