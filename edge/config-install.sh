# Install the vNext configuration file on the vCurrent mirror and enable switching between
# service roles.
# This script is intended to be run as root on the vCurrent mirror.

cp /etc/nginx/sites-enabled/ssl /etc/nginx/sites-available/vCurrent.conf
cp /etc/nginx/sites-available/vNext.conf /etc/nginx/sites-enabled/vNext.conf
rm /etc/nginx/sites-enabled/ssl
nginx -s reload
