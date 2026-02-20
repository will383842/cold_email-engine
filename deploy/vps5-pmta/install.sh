#!/bin/bash
# Script VPS5 — délègue au script générique VPS4 avec VPS_NUM=5
# USAGE :
#   DOMAIN1=mon-domaine.com IP1=1.2.3.4 \
#   DOMAIN2=second-domaine.com IP2=1.2.3.5 \
#   VPS1_IP=HETZNER_IP bash install.sh

VPS_NUM=5 exec bash "$(dirname "$0")/../vps4-pmta/install.sh" "$@"
