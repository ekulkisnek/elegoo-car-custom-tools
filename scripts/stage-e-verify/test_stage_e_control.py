#!/usr/bin/env python3
"""Stage E: unit tests for elegoo_control_map (no openpilot TCP)."""
from __future__ import annotations

import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_SCRIPTS = os.path.join(_REPO, "elegoo-car-custom-tools/scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest

from elegoo_control_map import (
    DEFAULT_CONTROL_CONFIG,
    ControlConfig,
    SpeedSmoother,
    map_torque_to_speed_single,
    map_torques_to_speed_pair,
)
from elegoo_openpilot_bridge import MAX_OP_TORQUE, torque_to_speed


def test_torque_to_speed_endpoints() -> None:
    assert torque_to_speed(-MAX_OP_TORQUE) == -255
    assert torque_to_speed(0) == 0
    assert torque_to_speed(MAX_OP_TORQUE) == 255


def test_default_pair_matches_independent_axes() -> None:
    cfg = DEFAULT_CONTROL_CONFIG
    for tl, tr in [(-500.0, -500.0), (0.0, 0.0), (250.0, -100.0)]:
        sl, sr = map_torques_to_speed_pair(tl, tr, cfg)
        assert sl == map_torque_to_speed_single(tl, cfg)
        assert sr == map_torque_to_speed_single(tr, cfg)


def test_deadband_zeros_small_torques() -> None:
    cfg = ControlConfig(deadband=20.0)
    sl, sr = map_torques_to_speed_pair(5.0, -5.0, cfg)
    assert sl == 0 and sr == 0
    sl, sr = map_torques_to_speed_pair(25.0, 0.0, cfg)
    assert sl != 0


def test_torque_scale_reduces_motion() -> None:
    cfg = ControlConfig(torque_scale=0.5)
    sl, _ = map_torques_to_speed_pair(500.0, 0.0, cfg)
    sl_full, _ = map_torques_to_speed_pair(500.0, 0.0, DEFAULT_CONTROL_CONFIG)
    assert sl < sl_full


def test_bias_shifts_speed() -> None:
    cfg = ControlConfig(bias_l=5, bias_r=-5)
    sl, sr = map_torques_to_speed_pair(0.0, 0.0, cfg)
    assert sl == 5
    assert sr == -5


def test_nonfinite_forces_neutral() -> None:
    sl, sr = map_torques_to_speed_pair(float("nan"), 0.0, DEFAULT_CONTROL_CONFIG)
    assert sl == 0 and sr == 0


def test_force_neutral() -> None:
    sl, sr = map_torques_to_speed_pair(500.0, 500.0, DEFAULT_CONTROL_CONFIG, force_neutral=True)
    assert sl == 0 and sr == 0


def test_speed_clamp() -> None:
    cfg = ControlConfig(speed_max=28)
    sl, sr = map_torques_to_speed_pair(500.0, 500.0, cfg)
    assert sl == 28 and sr == 28
    sl, sr = map_torques_to_speed_pair(-500.0, -500.0, cfg)
    assert sl == -28 and sr == -28


def test_smoother_lags_step() -> None:
    sm = SpeedSmoother(0.5)
    a, b = sm.step(50, 50)
    assert a < 50 and b < 50
    a2, b2 = sm.step(50, 50)
    assert a2 > a


def test_smoother_reset() -> None:
    sm = SpeedSmoother(0.3)
    sm.step(100, 100)
    sm.reset()
    x, y = sm.step(0, 0)
    assert x == 0 and y == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
