#!/bin/bash
mkdir -p tmp/etc/
mkdir -p tmp/log/
mkdir -p tmp/run/

certbot certonly \
    --text \
    --config-dir tmp/etc/ \
    --logs-dir tmp/log/ \
    --work-dir tmp/run/ \
    --test-cert \
    --dry-run \
    --authenticator dns-glesys \
    --dns-glesys-credentials credentials.ini \
    -d $1
