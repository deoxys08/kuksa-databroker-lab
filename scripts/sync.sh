#!/usr/bin/env bash
# Copy the repo to a Raspberry Pi over SSH (LAN).
# Usage: ./scripts/sync.sh <ssh-host>    e.g. ./scripts/sync.sh pi-a
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${1:?usage: sync.sh <ssh-host>}"
rsync -av --delete --exclude .git --exclude .venv --exclude __pycache__ --exclude .vssclient_history \
  ./ "${HOST}:~/kuksa-lab/"
