#!/usr/bin/env bash
# Kuksa Databroker'i rootless Podman ile baslatir (pi-a uzerinde calisir).
# Port yalnizca localhost + LAN IP'ye acilir (VPN/Tailscale arayuzune acilmaz).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && source .env
: "${PI_A_IP:?PI_A_IP tanimli degil. .env.example'i .env olarak kopyalayip doldur.}"

if ! ip -4 -o addr show | grep -q "inet ${PI_A_IP}/"; then
  echo "HATA: ${PI_A_IP} bu makinede yok. Mevcut IP'ler: $(hostname -I)" >&2
  exit 1
fi

IMG="${KUKSA_IMG:-ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.1}"
NAME=kuksa-databroker

podman rm -f "$NAME" >/dev/null 2>&1 || true
podman run -d --name "$NAME" \
  -p 127.0.0.1:55555:55555 \
  -p "${PI_A_IP}:55555:55555" \
  "$IMG" --address 0.0.0.0 --port 55555 --insecure

sleep 2
podman logs "$NAME" 2>&1 | grep -E "Starting|Populating|Listening"
