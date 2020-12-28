#!/bin/bash
source /etc/os-release
python3 setup.py bdist_rpm --release="1.${ID}${VERSION_ID}"
