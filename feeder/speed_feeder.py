#!/usr/bin/env python3
"""Simulated speed feeder (provider) for Eclipse Kuksa Databroker.

What it does:
- publishes Vehicle.Speed and Vehicle.Lab.Feeder.Heartbeat (sensors) every cycle
- publishes the VIN (attribute) after every (re)connect, validated against the VSS pattern
  because the broker does not enforce `pattern`
- reads the actuator targets Vehicle.Lab.Feeder.Mode / CycleTime, applies them and reports
  the applied values back as current values (desired state -> actual state)
- reconnects with backoff if the broker goes away (e.g. restart)
"""
import argparse
import logging
import os
import random
import re
import time

from kuksa_client.grpc import Datapoint, VSSClient

SPEED = "Vehicle.Speed"
VIN = "Vehicle.VehicleIdentification.VIN"
HEARTBEAT = "Vehicle.Lab.Feeder.Heartbeat"
MODE = "Vehicle.Lab.Feeder.Mode"
CYCLE_TIME = "Vehicle.Lab.Feeder.CycleTime"

# Pattern from VSS 6.0 (ISO 3779). Databroker 0.7.1 does not enforce it, so the provider does.
VIN_PATTERN = re.compile(r"^([0-9A-HJ-NPR-Z]{3})([0-9A-HJ-NPR-Z]{6})([0-9A-HJ-NPR-Z]{4}[0-9]{4})$")

# Driving profiles:
#   targets: range of target speeds (km/h)
#   accel:   max acceleration / deceleration (m/s^2)
#   hold:    seconds before a new target speed is chosen
PROFILES = {
    "CITY":        {"targets": (0.0, 50.0),    "accel": 1.5, "hold": (4.0, 10.0)},
    "HIGHWAY":     {"targets": (100.0, 130.0), "accel": 0.8, "hold": (8.0, 20.0)},
    "STOP_AND_GO": {"targets": (10.0, 25.0),   "accel": 2.0, "hold": (2.0, 5.0)},
}
DEFAULT_MODE = "CITY"
DEFAULT_CYCLE_MS = 200
CYCLE_MIN_MS, CYCLE_MAX_MS = 50, 5000  # same limits as vss/lab-overlay.json

log = logging.getLogger("feeder")


class SpeedSimulator:
    """Moves the speed towards a target speed with limited acceleration."""

    def __init__(self) -> None:
        self.speed = 0.0
        self.target = 0.0
        self.next_change = 0.0

    def new_target_now(self) -> None:
        self.next_change = 0.0

    def _pick_target(self, mode: str) -> float:
        lo, hi = PROFILES[mode]["targets"]
        if mode == "STOP_AND_GO":
            # alternate between standing still and creeping forward
            return 0.0 if self.target > 0.0 else random.uniform(lo, hi)
        return random.uniform(lo, hi)

    def step(self, mode: str, dt: float) -> float:
        profile = PROFILES[mode]
        now = time.monotonic()
        if now >= self.next_change:
            self.target = self._pick_target(mode)
            self.next_change = now + random.uniform(*profile["hold"])
        max_delta = profile["accel"] * 3.6 * dt  # m/s^2 -> km/h per step
        diff = self.target - self.speed
        self.speed += max(-max_delta, min(max_delta, diff))
        noise = random.uniform(-0.3, 0.3) if self.speed > 1.0 else 0.0
        return round(max(0.0, self.speed + noise), 1)


def value_of(datapoints: dict, path: str):
    dp = datapoints.get(path)
    return dp.value if dp is not None else None


def publish_static(client: VSSClient, vin: str) -> None:
    if VIN_PATTERN.match(vin):
        client.set_current_values({VIN: Datapoint(vin)})
        log.info("published VIN %s", vin)
    else:
        log.error("VIN %r does not match the VSS pattern, not publishing it", vin)


def run(host: str, port: int, vin: str) -> None:
    sim = SpeedSimulator()
    heartbeat = 0
    mode, cycle_ms = DEFAULT_MODE, DEFAULT_CYCLE_MS
    backoff = 1.0

    while True:
        try:
            with VSSClient(host, port) as client:
                log.info("connected to %s:%d", host, port)
                backoff = 1.0
                publish_static(client, vin)
                reported = None  # (mode, cycle_ms) last written as current values
                last_log = 0.0

                while True:
                    t0 = time.monotonic()

                    # 1) desired state: read actuator targets (None if nobody set one yet)
                    targets = client.get_target_values([MODE, CYCLE_TIME])
                    want_mode = value_of(targets, MODE)
                    want_cycle = value_of(targets, CYCLE_TIME)
                    if want_mode in PROFILES and want_mode != mode:
                        mode = want_mode
                        sim.new_target_now()
                    if want_cycle is not None and CYCLE_MIN_MS <= int(want_cycle) <= CYCLE_MAX_MS:
                        cycle_ms = int(want_cycle)

                    # 2) actual state: report what is really applied
                    if (mode, cycle_ms) != reported:
                        client.set_current_values({MODE: Datapoint(mode), CYCLE_TIME: Datapoint(cycle_ms)})
                        log.info("applied mode=%s cycle=%dms", mode, cycle_ms)
                        reported = (mode, cycle_ms)

                    # 3) sensors
                    speed = sim.step(mode, cycle_ms / 1000.0)
                    heartbeat = (heartbeat + 1) % 2**32
                    client.set_current_values({SPEED: Datapoint(speed), HEARTBEAT: Datapoint(heartbeat)})

                    if t0 - last_log >= 1.0:
                        log.info("speed=%5.1f km/h target=%5.1f hb=%d", speed, sim.target, heartbeat)
                        last_log = t0

                    time.sleep(max(0.0, cycle_ms / 1000.0 - (time.monotonic() - t0)))
        except Exception as exc:  # broker restart, network loss, ...
            log.warning("connection problem: %s - retrying in %.0fs", str(exc).splitlines()[0][:160], backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 10.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated speed feeder for Kuksa Databroker")
    parser.add_argument("--host", default=os.environ.get("KUKSA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("KUKSA_PORT", "55555")))
    parser.add_argument("--vin", default="LAB0TEST000000001", help="synthetic lab VIN")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # keep the client library quiet unless something is wrong
    logging.getLogger("kuksa_client").setLevel(logging.WARNING)
    try:
        run(args.host, args.port, args.vin)
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
