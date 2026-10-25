# 01 - Setup and workflow

## Why the port is bound to specific interfaces

The Pis have several interfaces (LAN, a VPN overlay, container bridges). Instead of
`--net=host`, the container publishes port 55555 explicitly:

```bash
-p 127.0.0.1:55555:55555 -p ${PI_A_IP}:55555:55555
```

Inside the container the broker listens on `0.0.0.0`; outside, only localhost and the LAN
address are reachable. Verify with `ss -tlnp | grep 55555`.

## Pitfalls hit during the lab

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` on 127.0.0.1:55555 after a reboot | Rootless Podman has no daemon; a container started with `podman run -d` is not restarted after reboot | Re-run `scripts/databroker-up.sh` (a systemd user unit would make it persistent) |
| `unexpected EOF while looking for matching "` in a script | A single quote inside `"${VAR:?message}"` starts a new quoted string in bash | Avoid `'` in such messages; check scripts with `bash -n` |
| `rsync --delete` removed a file on the Pi | The file (client history) was not in the repo | Exclude runtime files in `sync.sh` |
| Port binding fails after a reboot | DHCP may assign a different LAN IP | `databroker-up.sh` checks that `PI_A_IP` exists on the host before starting |

## Reading long Python tracebacks

Read from the bottom up and look for the root cause line. For example,
`Failed to connect to remote host: Connection refused` means nothing is listening on that
port. It is a TCP-level problem, not a Kuksa or gRPC problem.
