#!/usr/bin/env bash
# Copies ../../shared/classify_issue.py and label-policy.yaml into server/ (done automatically by run_local.sh and deploy.sh).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
sync_shared
