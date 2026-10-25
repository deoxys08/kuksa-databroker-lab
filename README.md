# Kuksa Databroker Lab

Hands-on lab: run **Eclipse Kuksa Databroker** with rootless **Podman** on a Raspberry Pi 5,
read / write / subscribe to **VSS** signals, add a custom VSS overlay, and write a small
Python feeder that publishes simulated vehicle speed.

> Personal learning project. All addresses, hostnames and vehicle data in this repo are
> placeholders or synthetic lab values.

## Background in two sentences

- **VSS (COVESA Vehicle Signal Specification)** is a standard tree of vehicle signal names and
  types, e.g. `Vehicle.Speed` (float, km/h). Applications use these names instead of CAN IDs/DBCs.
- **Kuksa Databroker** is a small in-vehicle gRPC server (written in Rust) that holds the
  *current* value of every VSS signal in memory and lets providers write and consumers read
  or subscribe.

## Lab topology

```
  pi-b (sensor ECU)            pi-a (vehicle computer)            Mac (developer)
┌──────────────────┐  gRPC   ┌───────────────────────────┐ gRPC ┌──────────────────────┐
│ Python feeder    │ ──────► │ Podman: kuksa-databroker  │ ───► │ kuksa-client         │
│ (simulated speed)│   LAN   │ VSS 6.0 + custom overlay  │ LAN  │ repo, editor, monitor│
└──────────────────┘         │ :55555 (localhost + LAN)  │      └──────────────────────┘
                             └───────────────────────────┘
```

| Device | Role | Platform |
|---|---|---|
| `pi-a` | Databroker | Raspberry Pi 5, Debian 12 (bookworm), Podman 4.3.1 |
| `pi-b` | Feeder (provider) | Raspberry Pi 5, Podman 5.4.2, Python 3.13 |
| Mac | Repo, development, monitoring | macOS, Apple Silicon, Python 3.14 |

Code is edited and committed on the Mac and copied to the Pis with `rsync`.
The Pis hold no Git credentials.

## Tested versions

| Component | Version |
|---|---|
| Kuksa Databroker | `0.7.1` (`ghcr.io/eclipse-kuksa/kuksa-databroker:0.7.1`) |
| VSS (bundled in image) | `6.0` |
| kuksa-client (PyPI) | `0.6.0` |

## Repository layout

```
.env.example              # template for local IPs (.env itself is git-ignored)
scripts/
  databroker-up.sh        # start Databroker on pi-a (rootless Podman)
  sync.sh                 # rsync this repo to a Pi
docs/
  01-setup-and-workflow.md
  02-cli-basics.md
```

## Quick start

1. Create your local config:

   ```bash
   cp .env.example .env    # fill in PI_A_IP / PI_B_IP (LAN addresses)
   ```

2. Add SSH aliases on the Mac (`~/.ssh/config`), using LAN IPs:

   ```
   Host pi-a
     HostName <PI_A_LAN_IP>
     User <user>
   Host pi-b
     HostName <PI_B_LAN_IP>
     User <user>
   ```

3. Deploy and start the Databroker:

   ```bash
   ./scripts/sync.sh pi-a
   ssh pi-a '~/kuksa-lab/scripts/databroker-up.sh'
   ```

4. Connect from any machine on the LAN:

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install kuksa-client
   kuksa-client grpc://<PI_A_LAN_IP>:55555
   ```

## Security note

The Databroker runs with `--insecure` (no TLS, no authorization). The port is therefore
published **only on localhost and the LAN interface**, never on VPN/overlay interfaces,
and should not be exposed beyond a trusted lab network.

## Lab progress

- [x] 1. Environment check
- [x] 2. Databroker in rootless Podman
- [x] 3. Repo and Mac-to-Pi workflow
- [x] 4. CLI: read, write, subscribe; sensor vs attribute vs actuator
- [ ] 5. Custom VSS overlay
- [ ] 6. Python feeder on pi-b, live monitoring from the Mac
- [ ] 7. Wrap-up
