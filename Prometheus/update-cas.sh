#!/bin/sh

TMP_DIR=$(mktemp -d)
GIT_REPO="sdn-sense/rm-configs"
CA_DIR=/etc/grid-security/certificates

cd $TMP_DIR
git clone https://github.com/$GIT_REPO .

cd $TMP_DIR/CAs/
for fname in `ls *.pem`; do
  cp $fname $CA_DIR/
  hash=$(openssl x509 -hash -in "$CA_DIR/$fname" |head -n 1)
  ln -sf $CA_DIR/$fname $CA_DIR/$hash.0
done

rm -rf $TMP_DIR
# Also get Let's Encrypt CAs
TMP_DIR=$(mktemp -d)
cd $TMP_DIR/
# Copy of https://github.com/cilogon/letsencrypt-certificates.git
git clone https://github.com/sdn-sense/letsencrypt-certificates.git
cd letsencrypt-certificates/
make check
make install
rm -rf $TMP_DIR
