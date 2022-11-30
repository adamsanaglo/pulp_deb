# Install the vNext configuration file on the vCurrent mirror and enable switching between
# service roles.
# This script assumes it, and the tarball containing it, were unpacked in the same directory.
# It also assumes that the tarball was unpacked as root, and that the current user has sudo.
#
# The newly-installed configuration file is enabled if and only if the parameter "activate"
# is passed to this script.
#
# Usage:   config-install.sh [activate]

activate="$1"

sudo install -o root -g root -m 555 -t /usr/local/bin config-activate.sh log-analyze

available=/etc/nginx/sites-available
enabled=/etc/nginx/sites-enabled

# Save vCurrent configuration file so we can switch back to it.
# Leave it in place, renamed; if nginx restarts, it will use it.
if [ -f $enabled/ssl ]; then
    sudo mv $enabled/ssl $enabled/vCurrent.conf
fi
if [ -f $enabled/vCurrent.conf]; then
    sudo cp $enabled/vCurrent.conf $available
fi

# Install vNext configuration file.
sudo cp sites-available/vNext.conf $available/vNext.conf

if [ "$activate" = "activate" ]; then
    # Activate the vNext configuration file.
    sudo /usr/local/bin/config-activate.sh vNext
fi
