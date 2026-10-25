# 04 - Python feeder and live monitoring

## Roles

| Host | Process | Role |
|---|---|---|
| `pi-b` | `feeder/speed_feeder.py` (via `scripts/feeder-up.sh`) | Provider: writes sensors, applies actuators |
| `pi-a` | `kuksa-databroker` | Broker |
| Mac | `feeder/monitor.py` | Consumer: subscribes and prints one line per cycle |
| Mac | `kuksa-client` | Sends actuator commands (`setTargetValue`) |

## What the feeder does

Every cycle:

1. **Desired state** - reads the targets of `Vehicle.Lab.Feeder.Mode` and `Vehicle.Lab.Feeder.CycleTime`.
2. **Actual state** - when something changed, applies it and writes the applied values back
   as *current* values of the same actuators.
3. **Sensors** - computes the next speed for the active profile (bounded acceleration plus a
   little noise) and writes `Vehicle.Speed` and `Vehicle.Lab.Feeder.Heartbeat`.

After every (re)connect it publishes the VIN, validated against the VSS `pattern`
(the broker does not enforce it, see `03-vss-and-custom-overlay.md`).

| Profile | Target speeds | Max accel/decel |
|---|---|---|
| `CITY` | 0 - 50 km/h | 1.5 m/s² |
| `HIGHWAY` | 100 - 130 km/h | 0.8 m/s² |
| `STOP_AND_GO` | alternates 0 and 10 - 25 km/h | 2.0 m/s² |

## Running it

```bash
# pi-b
~/kuksa-lab/scripts/feeder-up.sh

# Mac, terminal 2
source .env && source .venv/bin/activate
python feeder/monitor.py --host "$PI_A_IP"

# Mac, terminal 3
kuksa-client grpc://${PI_A_IP}:55555
setTargetValue Vehicle.Lab.Feeder.Mode HIGHWAY
setTargetValue Vehicle.Lab.Feeder.CycleTime 1000
```

## Observations

- **Existing targets are applied on startup.** The feeder came up in `HIGHWAY / 200 ms`
  because those targets were still stored in the broker from an earlier test.
- **CycleTime is honoured.** The heartbeat rose by 5/s at 200 ms, 1/s at 1000 ms and 10/s at 100 ms.
- **Command latency is up to one cycle** because targets are polled each cycle.
- **Deceleration is physical.** Switching from `HIGHWAY` to `STOP_AND_GO` brought the speed
  from 118 km/h to 0 at about 7 km/h per second (2 m/s² × 3.6).
- **One notification per signal.** Speed and Heartbeat are written in one request, but a
  subscriber receives them as separate updates. `monitor.py` therefore prints on Heartbeat.
- **VSS `float` is 32-bit.** A value written as 23.2 is read back as 23.200000762939453;
  format floats for display.

## Broker restart while the feeder runs

```
20:43:24.507 WARNING connection problem: ... Connection refused - retrying in 1s
20:43:25.533 INFO connected to <PI_A_LAN_IP>:55555
20:43:25.550 INFO published VIN LAB0TEST000000001
20:43:25.570 INFO applied mode=STOP_AND_GO cycle=100ms
```

- The feeder reconnected after about one second and re-published the VIN, which the broker
  had lost (memory only).
- The broker's actuator targets were empty after the restart, yet the feeder kept its last
  applied state and reported it again as current value. A missing target means "no new
  request", not "reset" - just as a physical actuator keeps its state when a broker restarts.
- The heartbeat continued counting (121 -> 130); the counter lives in the provider.

## Possible improvements

- Subscribe to actuator targets instead of polling, to remove the command latency.
- Use the `kuksa.val.v2` provider API so that actuation requests are routed to the feeder
  and rejected by the broker when no provider is connected.
- Run the feeder and the broker as Podman containers managed by systemd user units
  (survive reboots), or as Ankaios workloads.
- Add reconnect logic to `monitor.py`.
- Enable TLS and token-based authorization on the broker.
