#!/usr/bin/env python3
"""Compact live view of the lab signals (subscribe, one line per update)."""
import argparse
import logging
import os
import time

from kuksa_client.grpc import VSSClient

SPEED = "Vehicle.Speed"
HEARTBEAT = "Vehicle.Lab.Feeder.Heartbeat"
MODE = "Vehicle.Lab.Feeder.Mode"
CYCLE_TIME = "Vehicle.Lab.Feeder.CycleTime"
PATHS = [SPEED, HEARTBEAT, MODE, CYCLE_TIME]


def fmt(value, width: int) -> str:
    if value is None:
        text = "-"
    elif isinstance(value, float):
        # VSS `float` is 32-bit; print one decimal instead of float32 artifacts like 23.200000762939453
        text = f"{value:.1f}"
    else:
        text = str(value)
    return f"{text:>{width}}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Live view of lab signals")
    parser.add_argument("--host", default=os.environ.get("KUKSA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("KUKSA_PORT", "55555")))
    args = parser.parse_args()
    logging.getLogger("kuksa_client").setLevel(logging.WARNING)

    state = {}
    try:
        with VSSClient(args.host, args.port) as client:
            print(f"subscribed to {', '.join(PATHS)} on {args.host}:{args.port}")
            for updates in client.subscribe_current_values(PATHS):
                for path, dp in updates.items():
                    if dp is not None:
                        state[path] = dp.value
                # The broker sends one notification per changed signal, so a single feeder cycle
                # (Speed + Heartbeat) arrives as two updates. Print once per cycle (on Heartbeat)
                # and whenever an actuator value changes.
                if not ({HEARTBEAT, MODE, CYCLE_TIME} & set(updates)):
                    continue
                print(
                    f"{time.strftime('%H:%M:%S')}  "
                    f"speed={fmt(state.get(SPEED), 6)} km/h  "
                    f"hb={fmt(state.get(HEARTBEAT), 6)}  "
                    f"mode={fmt(state.get(MODE), 11)}  "
                    f"cycle={fmt(state.get(CYCLE_TIME), 4)} ms",
                    flush=True,
                )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
