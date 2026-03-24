#!/usr/bin/env python3
"""Helpers for speaking the stock ELEGOO ESP32<->UNO JSON protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
import itertools
import time
from typing import Any


HEARTBEAT_FRAME = "{Heartbeat}"
STOP_FRAME = '{"N":100}'
DEFAULT_PORT = 100


class Direction:
    LEFT = 1
    RIGHT = 2
    FORWARD = 3
    BACKWARD = 4


class RockerDirection:
    FORWARD = 1
    BACKWARD = 2
    LEFT = 3
    RIGHT = 4
    LEFT_FORWARD = 5
    LEFT_BACKWARD = 6
    RIGHT_FORWARD = 7
    RIGHT_BACKWARD = 8
    STOP = 9


class MotorSelection:
    BOTH = 0
    RIGHT_A = 1
    LEFT_B = 2


class MotorDirection:
    STOP = 0
    FORWARD = 1
    BACKWARD = 2


def compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"))


def framed_json(payload: dict[str, Any]) -> str:
    return compact_json(payload)


def with_header(payload: dict[str, Any], prefix: str) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["H"] = f"{prefix}_{int(time.time() * 1000)}_{next(_HEADER_COUNTER)}"
    return enriched


def cmd_stop() -> str:
    return STOP_FRAME


def cmd_car_timed(direction: int, speed: int, duration_ms: int, header_prefix: str = "car_timed") -> str:
    return framed_json(with_header({"N": 2, "D1": direction, "D2": speed, "T": duration_ms}, header_prefix))


def cmd_car_untimed(direction: int, speed: int, header_prefix: str = "car_untimed") -> str:
    return framed_json(with_header({"N": 3, "D1": direction, "D2": speed}, header_prefix))


def cmd_motor_control(selection: int, direction: int, speed: int, header_prefix: str = "motor_ctl") -> str:
    return framed_json(with_header({"N": 1, "D1": selection, "D2": speed, "D3": direction}, header_prefix))


def cmd_motor_speed(left_speed: int, right_speed: int, header_prefix: str = "motor_speed") -> str:
    return framed_json(with_header({"N": 4, "D1": left_speed, "D2": right_speed}, header_prefix))


def cmd_rocker(direction: int, header_prefix: str = "rocker") -> str:
    return framed_json(with_header({"N": 102, "D1": direction}, header_prefix))


@dataclass(frozen=True)
class ExpectedMotion:
    label: str
    firmware_basis: str
    expected_vehicle_motion: str


EXPECTATIONS: dict[str, ExpectedMotion] = {
    "stop": ExpectedMotion(
        label="Stop",
        firmware_basis='ESP32 and UNO both use {"N":100} as standby/stop.',
        expected_vehicle_motion="Car should stop and remain still.",
    ),
    "car_left": ExpectedMotion(
        label="Car Left",
        firmware_basis="N=3 with D1=1 maps to Left.",
        expected_vehicle_motion="Car should pivot or arc left depending on traction.",
    ),
    "car_right": ExpectedMotion(
        label="Car Right",
        firmware_basis="N=3 with D1=2 maps to Right.",
        expected_vehicle_motion="Car should pivot or arc right depending on traction.",
    ),
    "car_forward": ExpectedMotion(
        label="Car Forward",
        firmware_basis="N=3 with D1=3 maps to Forward.",
        expected_vehicle_motion="Car should move forward.",
    ),
    "car_backward": ExpectedMotion(
        label="Car Backward",
        firmware_basis="N=3 with D1=4 maps to Backward.",
        expected_vehicle_motion="Car should move backward.",
    ),
    "rocker_left_forward": ExpectedMotion(
        label="Rocker Left-Forward",
        firmware_basis="N=102 with D1=5 maps to LeftForward.",
        expected_vehicle_motion="Car should move forward while veering left.",
    ),
    "rocker_right_forward": ExpectedMotion(
        label="Rocker Right-Forward",
        firmware_basis="N=102 with D1=7 maps to RightForward.",
        expected_vehicle_motion="Car should move forward while veering right.",
    ),
    "single_right_forward": ExpectedMotion(
        label="Single Right Motor Forward",
        firmware_basis="N=1 with D1=1 selects motor A, documented as Right in driver code.",
        expected_vehicle_motion="Right motor only should drive; car should yaw left.",
    ),
    "single_left_forward": ExpectedMotion(
        label="Single Left Motor Forward",
        firmware_basis="N=1 with D1=2 selects motor B, documented as Left in driver code.",
        expected_vehicle_motion="Left motor only should drive; car should yaw right.",
    ),
    "differential_forward_left_bias": ExpectedMotion(
        label="Differential Forward Left Bias",
        firmware_basis="N=4 writes left and right PWM separately, both forward.",
        expected_vehicle_motion="Car should move forward and arc toward the slower side.",
    ),
}
_HEADER_COUNTER = itertools.count(1)
