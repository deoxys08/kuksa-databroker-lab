# 02 - CLI basics: read, write, subscribe

Client: `kuksa-client grpc://127.0.0.1:55555` (on pi-a) or `grpc://<PI_A_LAN_IP>:55555` (from the LAN).

## Commands used

```
getMetaData Vehicle.Speed
getValue Vehicle.Speed
setValue Vehicle.Speed 72.5
subscribe Vehicle.Speed
setTargetValue Vehicle.Body.Lights.Beam.Low.IsOn true
```

## Observations

- **No value is not zero.** Before anyone writes, `getValue Vehicle.Speed` returns only the
  path, with no `value` field. Consumers must distinguish "speed is 0" from "no data yet".
- **Subscribe pushes.** The first notification carries the current value; afterwards only
  changes are pushed. No polling.
- **Typed signals.** `setValue Vehicle.Speed fast` fails (`ValueError in casting the value`).
  The client casts using the metadata type (`FLOAT`); the gRPC API itself is typed as well.
- **Metadata comes from VSS.** `data_type`, `unit` and `description` are defined in the VSS
  file loaded at startup, not sent with the value.
- **State lives in the broker, not in the client.** Values written from one client session
  are readable later from another machine. They survive client disconnects but are lost
  when the broker process stops (memory only, latest value only, no history).
  Providers must therefore re-publish attributes such as the VIN after a broker restart.
- **Timestamps are UTC.**

## Signal types (`entry_type`)

| Type | Example | Changes | Written by | Read by |
|---|---|---|---|---|
| `SENSOR` | `Vehicle.Speed` | Continuously | Provider (feeder, CAN bridge) | Applications (read / subscribe) |
| `ATTRIBUTE` | `Vehicle.VehicleIdentification.VIN` | Practically never | Provider, typically once at startup | Applications |
| `ACTUATOR` | `Vehicle.Body.Lights.Beam.Low.IsOn` | On command | App writes **target**, provider writes **current** | Everyone |

An actuator has two values: the **target** (desired state, requested by an application)
and the **current** value (actual state, reported by the provider that controls the
hardware). This mirrors the desired/actual state pattern used by orchestrators.
A successful `setTargetValue` only means the request was stored; without a provider,
nothing is actuated.
