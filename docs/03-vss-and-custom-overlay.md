# 03 - VSS and a custom overlay

## What VSS looks like

VSS is a tree. `branch` nodes group signals; leaves are the actual signals and have one of
three types: `sensor`, `attribute` or `actuator`.

The VSS 6.0 release bundled with Databroker 0.7.1 contains **1263 leaves**:

| Type | Count |
|---|---|
| actuator | 643 |
| sensor | 490 |
| attribute | 130 |

Each leaf carries a contract. `type` and `datatype` are mandatory; `description`, `unit`,
`min`, `max`, `allowed`, `default` and `pattern` are optional. Example from the release file:

```json
"Speed": {
  "datatype": "float",
  "description": "Vehicle speed.",
  "type": "sensor",
  "unit": "km/h"
}
```

The source format of VSS is `.vspec` (YAML based). COVESA's `vss-tools` converts it into the
JSON format that Databroker loads. In this lab the overlay is written directly in JSON.

## How the image loads VSS

```
Entrypoint = /app/databroker      WorkDir = /
KUKSA_DATABROKER_METADATA_FILE = vss_release_6.0.json
```

- The environment variable is the default for `--vss`. The image ships
  `/vss_release_5.1.json` and `/vss_release_6.0.json`.
- `--vss` accepts a **comma-separated list** of files, which are merged into one tree.
- **Pitfall:** passing `--vss` replaces the default. The standard release must be listed
  explicitly, otherwise the broker only knows the overlay signals.

To inspect the bundled file (the image may have no shell):

```bash
podman export kuksa-databroker | tar -xO vss_release_6.0.json > /tmp/vss_release_6.0.json
```

## The lab overlay

`vss/lab-overlay.json` adds the branch `Vehicle.Lab.Feeder`, used by the feeder in step 6:

| Signal | Type | Datatype | Restriction / default | Purpose |
|---|---|---|---|---|
| `Heartbeat` | sensor | uint32 | | Incremented every publish cycle; detects a stalled feeder |
| `Version` | attribute | string | `default: "0.1.0"` | Static information |
| `Mode` | actuator | string | `allowed: CITY, HIGHWAY, STOP_AND_GO` | Driving profile, commanded from outside |
| `CycleTime` | actuator | uint16 (ms) | `min: 50`, `max: 5000` | Publish interval, commanded from outside |

It is mounted read-only and loaded next to the standard release
(see `scripts/databroker-up.sh`):

```bash
-v "$(pwd)/vss:/vss:ro"
--vss /vss_release_6.0.json,/vss/lab-overlay.json
```

## Observations

- Both files appear in the log (`Populating metadata from file ...`). The `Vehicle` branch
  exists in both and is merged without conflict.
- **Defaults are applied at startup.** `Vehicle.Lab.Feeder.Version` reads `0.1.0` with the
  broker start time as timestamp, without anyone writing it. Static values can therefore
  survive a broker restart via the VSS file; vehicle-specific values (e.g. the VIN) still
  have to be published by a provider.
- `allowed`, `min` and `max` are exposed to clients as `value_restriction` in the metadata.

## Restriction enforcement (Databroker 0.7.1)

| Write | Result |
|---|---|
| `setTargetValue Vehicle.Lab.Feeder.Mode HIGHWAY` | OK |
| `setTargetValue Vehicle.Lab.Feeder.Mode TURBO` | 400 `value out of allowed bounds` |
| `setTargetValue Vehicle.Lab.Feeder.CycleTime 200` | OK |
| `setTargetValue Vehicle.Lab.Feeder.CycleTime 10` | 400 `value out of min/max bounds` |
| `setTargetValue Vehicle.Lab.Feeder.CycleTime 70000` | 400 `value out of min/max bounds` (the `max: 5000` check triggers before the uint16 range matters) |
| `setValue Vehicle.VehicleIdentification.VIN HELLO` | **OK** - `pattern` is not enforced |

Takeaways:

- A rejected write leaves the previously stored value unchanged.
- `allowed`, `min` and `max` are enforced by the broker; `pattern` is documentation only.
  Providers must validate pattern-constrained values (such as the VIN) themselves.
