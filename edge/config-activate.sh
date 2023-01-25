#!/bin/bash
# Switch the active nginx configuration

goal="${1,,}"   # lowercase the argument
if [ "$goal" = "vnext" ]; then
    cp /etc/nginx/sites-available/vNext.conf /etc/nginx/sites-enabled/vNext.conf
    rm -f /etc/nginx/sites-enabled/vCurrent.conf
elif [ "$goal" = "vcurrent" ]; then
    cp /etc/nginx/sites-available/vCurrent.conf /etc/nginx/sites-enabled/vCurrent.conf
    rm -f /etc/nginx/sites-enabled/vNext.conf
else
    echo "Usage: $0 vnext|vcurrent"
    exit 1
fi
nginx -s reload

# Sanity tests
# 1) Should be able to download an "old path" rpm, validating ssl.
curl --head --silent --output /tmp/myfile --resolve 'packages.microsoft.com:443:127.0.0.1' --resolve 'packages.microsoft.com:80:127.0.0.1' -L https://packages.microsoft.com/yumrepos/amlfs-el7/amlfs-lustre-client-2.15.1_24_gbaa21ca-3.10.0.1160.41.1.el7-1.noarch.rpm
if [ "$?" = "0" ]; then
  echo "Warning: downloading old-path rpm failed sanity check!"
fi

# 2) If we enabled vnext we should be able to download a "new path" rpm, validating ssl.
if [ "$goal" = "vnext" ]; then
  curl --head --silent --output /tmp/myfile --resolve 'packages.microsoft.com:443:127.0.0.1' --resolve 'packages.microsoft.com:80:127.0.0.1' -L https://packages.microsoft.com/yumrepos/amlfs-el7/Packages/a/amlfs-lustre-client-2.15.1_24_gbaa21ca-3.10.0.1160.41.1.el7-1.noarch.rpm
  if [ "$?" = "0" ]; then
    echo "Warning: downloading new-path rpm failed sanity check!"
  fi
fi
rm /tmp/myfile
