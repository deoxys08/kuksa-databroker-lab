#!/usr/bin/env bash
# Run the speed feeder in the foreground (intended for pi-b).
# Connects to the Databroker on pi-a over the LAN. Extra arguments are passed to the feeder.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && source .env
: "${PI_A_IP:?PI_A_IP is not set. Copy .env.example to .env and fill it in.}"

if [ ! -x .venv/bin/python ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
fi
.venv/bin/pip install --quiet -r feeder/requirements.txt

exec .venv/bin/python feeder/speed_feeder.py --host "$PI_A_IP" --port 55555 "$@"
