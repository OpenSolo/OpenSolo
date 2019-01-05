#!/bin/bash

cd $(dirname $0)

set -e
rm -rf static
mkdir -p static
while read -r p && [[ "$p" != '' ]]; do
  cp ../build/tmp-eglibc/deploy/rpm/$p static/
done <packages
cd static
createrepo .
aws s3 sync . s3://solo-packages/3.10.17-rt12/ --acl public-read --delete
