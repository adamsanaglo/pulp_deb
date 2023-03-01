#!/bin/bash
# Switch the active nginx configuration

function usage {
    echo "Usage: $0 vnext|vcurrent sha256_checksum"
    exit 1
}

function check_checksum {
    file="$1"
    expected="$2"
    if ! sha256sum --status -c <<<"$expected  $file"; then
        echo "Checksum failure: sha256sum($file) != [$expected]"
        exit 1
    fi
}

goal="${1,,}"   # lowercase the argument
checksum="$2"
if [ -z "$goal" -o -z "$checksum" ]; then
    usage
fi

if [ "$goal" = "vnext" ]; then
    check_checksum /etc/nginx/sites-available/vNext.conf "$checksum"
    cp /etc/nginx/sites-available/vNext.conf /etc/nginx/sites-enabled/vNext.conf
    rm -f /etc/nginx/sites-enabled/vCurrent.conf
elif [ "$goal" = "vcurrent" ]; then
    check_checksum /etc/nginx/sites-available/vCurrent.conf "$checksum"
    cp /etc/nginx/sites-available/vCurrent.conf /etc/nginx/sites-enabled/vCurrent.conf
    rm -f /etc/nginx/sites-enabled/vNext.conf
else
    usage
fi
nginx -s reload
sleep 3

function testPkgUrl() {
    path="$1"
    msg="$2"
    pmc="packages.microsoft.com"
    if ! curl --fail --head --silent --output /dev/null --resolve "${pmc}:443:127.0.0.1" --resolve "${pmc}:80:127.0.0.1" -L https://${pmc}/${path}; then
        echo "Warning: downloading ${msg} failed sanity check!"
    else
        echo "OK: downloaded ${msg} successfully"
    fi
}

# Sanity tests
# 1) Should be able to download an "old path" rpm, validating ssl.
testPkgUrl "yumrepos/amlfs-el7/amlfs-lustre-client-2.15.1_24_gbaa21ca-3.10.0.1160.41.1.el7-1.noarch.rpm" "old-path-rpm"

# 2) Folder urls without trailing slash should result in a 301/redirect
if ! curl -s --head http://127.0.0.1/yumrepos | grep -q "^HTTP/1.1 301"; then
    echo "Warning: folder redirects (301) aren't being handled properly!"
else
    echo "OK: folder redirects handled properly"
fi

# 3) If we enabled vnext we should be able to download a "new path" rpm, validating ssl.
if [ "$goal" = "vnext" ]; then
    testPkgUrl "yumrepos/amlfs-el7/Packages/a/amlfs-lustre-client-2.15.1_24_gbaa21ca-3.10.0.1160.41.1.el7-1.noarch.rpm" "new-path-rpm"
fi

# 4) Directory listing of APT /dists/ metadata folder can be retrieved
testPkgUrl "ubuntu/22.04/prod/dists" "APT metadata directory without trailing slash"
testPkgUrl "ubuntu/22.04/prod/dists/" "APT metadata directory with trailing slash"

# 5) Ensure all required metadata files in an APT pocket can be retrieved
for metafile in "Release" "Release.gpg" "InRelease"; do
    testPkgUrl "ubuntu/20.04/prod/dists/focal/$metafile" "APT $metafile"
done
