#!/usr/bin/env bash
# Start Eclipse Kuksa Databroker with rootless Podman (runs on pi-a).
# The port is published only on localhost and the LAN IP, never on VPN/Tailscale interfaces.
# Loads the standard VSS release bundled in the image plus the lab overlay from ./vss.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && source .env
: "${PI_A_IP:?PI_A_IP is not set. Copy .env.example to .env and fill it in.}"

if ! ip -4 -o addr show | grep -q "inet ${PI_A_IP}/"; then
  echo "ERROR: ${PI_A_IP} is not assigned to this host. Current IPs: $(hostname -I)" >&2
  exit 1
fi

IMG="${KUKSA_IMG:-ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.1}"
NAME=kuksa-databroker
VSS_FILES="/vss_release_6.0.json,/vss/lab-overlay.json"

podman rm -f "$NAME" >/dev/null 2>&1 || true
podman run -d --name "$NAME" \
  -p 127.0.0.1:55555:55555 \
  -p "${PI_A_IP}:55555:55555" \
  -v "$(pwd)/vss:/vss:ro" \
  "$IMG" --address 0.0.0.0 --port 55555 --insecure --vss "$VSS_FILES"

sleep 2
podman logs "$NAME" 2>&1 | grep -E "Starting|Populating|Listening|ERROR|WARN"
