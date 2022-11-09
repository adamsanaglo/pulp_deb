# Install the vNext configuration file on the vCurrent mirror and enable switching between
# service roles.
# This script assumes it, and the tarball containing it, were unpacked in the same directory.
# It also assumes that the tarball was unpacked as root, and that the current user has sudo.

sudo install -o root -g root -m 555 -t /usr/local/bin config-activate.sh log-analyze

available=/etc/nginx/sites-available

# Save vCurrent configuration file so we can switch back to it.
# Leave it in place, renamed; if nginx restarts, it will use it.
sudo mv /etc/nginx/sites-enabled/ssl /etc/nginx/sites-enabled/vCurrent.conf
sudo cp /etc/nginx/sites-enabled/vCurrent.conf $available

# Install vNext configuration file.
sudo cp sites-available/vNext.conf $available/vNext.conf

# Activate the vNext configuration file.
sudo /usr/local/bin/config-activate.sh vNext
