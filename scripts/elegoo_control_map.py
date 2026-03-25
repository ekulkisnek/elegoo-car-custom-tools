#!/usr/bin/env python3
"""
Stage E: torque (comma_body TORQUE_L/R) → signed motor speed for ELEGOO.

The ELEGOO N=4 command uses unsigned speed (0=stop, 255=max), always forward.
For bidirectional per-motor control, we use N=1 commands instead.

This module maps torque to signed speed: -255 (full reverse) to +255 (full forward).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


NEUTRAL_SPEED = 0


@dataclass(frozen=True)
class ControlConfig:
    """Tuning knobs (defaults preserve Stage D behavior)."""

    max_op_torque: float = 500.0
    deadband: float = 0.0
    torque_scale: float = 1.0
    gain_l: float = 1.0
    gain_r: float = 1.0
    bias_l: int = 0
    bias_r: int = 0
    speed_max: int = 255
    speed_min: int = 0
    stale_sendcan_sec: float = 0.0
    smooth_alpha: float = 1.0


DEFAULT_CONTROL_CONFIG = ControlConfig()


def sendcan_is_stale(now_mono: float, last_rx_mono: float, threshold_sec: float) -> bool:
    """True if watchdog says sendcan is too old. threshold_sec <= 0 disables (never stale)."""
    if threshold_sec <= 0.0:
        return False
    return (now_mono - last_rx_mono) >= threshold_sec


def clamp_speed(x: float, cfg: ControlConfig) -> int:
    """Clamp to [-speed_max, +speed_max]."""
    v = int(round(x))
    return max(-cfg.speed_max, min(cfg.speed_max, v))


def torque_to_speed_linear(torque: float, max_op_torque: float) -> int:
    """Map one torque in [-max, max] to [-255, +255]."""
    m = float(max_op_torque)
    t = max(-m, min(m, float(torque)))
    return int(round(t / m * 255.0))


def apply_deadband(t: float, deadband: float) -> float:
    if abs(t) < deadband:
        return 0.0
    return t


def map_torques_to_speed_pair(
    torque_l: float,
    torque_r: float,
    cfg: ControlConfig,
    *,
    force_neutral: bool = False,
) -> tuple[int, int]:
    """
    Full open-loop map: deadband → gains → scale → clip torque → linear → bias → speed clamp.

    Returns signed speeds in [-speed_max, +speed_max].  0 = stop.
    If force_neutral or non-finite inputs, returns (0, 0) + bias clamped.
    """
    if force_neutral or not (math.isfinite(torque_l) and math.isfinite(torque_r)):
        sl = clamp_speed(float(NEUTRAL_SPEED + cfg.bias_l), cfg)
        sr = clamp_speed(float(NEUTRAL_SPEED + cfg.bias_r), cfg)
        return sl, sr

    tl = apply_deadband(torque_l, cfg.deadband)
    tr = apply_deadband(torque_r, cfg.deadband)
    tl *= cfg.gain_l * cfg.torque_scale
    tr *= cfg.gain_r * cfg.torque_scale
    m = cfg.max_op_torque
    tl = max(-m, min(m, tl))
    tr = max(-m, min(m, tr))

    sl = torque_to_speed_linear(tl, m)
    sr = torque_to_speed_linear(tr, m)
    sl = clamp_speed(sl + cfg.bias_l, cfg)
    sr = clamp_speed(sr + cfg.bias_r, cfg)

    if cfg.speed_min > 0:
        if abs(sl) < cfg.speed_min:
            sl = 0
        if abs(sr) < cfg.speed_min:
            sr = 0

    return sl, sr


class SpeedSmoother:
    """Exponential moving average on signed speed integers (reduces jerk / chatter)."""

    def __init__(self, alpha: float, neutral: int = NEUTRAL_SPEED) -> None:
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.neutral = neutral
        self.speed_l = float(neutral)
        self.speed_r = float(neutral)

    def reset(self) -> None:
        self.speed_l = float(self.neutral)
        self.speed_r = float(self.neutral)

    def step(self, target_l: int, target_r: int) -> tuple[int, int]:
        if self.alpha >= 1.0:
            return target_l, target_r
        a = self.alpha
        self.speed_l = a * target_l + (1.0 - a) * self.speed_l
        self.speed_r = a * target_r + (1.0 - a) * self.speed_r
        return int(round(self.speed_l)), int(round(self.speed_r))


def map_torque_to_speed_single(torque: float, cfg: ControlConfig) -> int:
    """One-axis map (for tests matching legacy torque_to_speed behavior)."""
    sl, _ = map_torques_to_speed_pair(torque, 0.0, cfg)
    return sl
