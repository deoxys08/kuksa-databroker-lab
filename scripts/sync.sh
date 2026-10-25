#!/usr/bin/env bash
# Repoyu bir Pi'ye kopyalar. Kullanim: ./scripts/sync.sh pi-a
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${1:?kullanim: sync.sh <ssh-host>}"
rsync -av --delete --exclude .git --exclude .venv --exclude __pycache__ \
  ./ "${HOST}:~/kuksa-lab/"
