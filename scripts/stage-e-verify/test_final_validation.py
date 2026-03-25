#!/usr/bin/env python3
"""
Final computational validation tests for control map and launcher configuration.

LIVE_CFG: original conservative config (torque_scale=0.35, speed_max=50).
TUNED_CFG: tuned for visible wheel motion (torque_scale=2.0, speed_max=100).

No car or openpilot manager needed — pure math.
"""
from __future__ import annotations

import math
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_SCRIPTS = os.path.join(_REPO, "elegoo-car-custom-tools/scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest
import numpy as np

from elegoo_control_map import (
    ControlConfig,
    SpeedSmoother,
    map_torques_to_speed_pair,
    sendcan_is_stale,
)

LIVE_CFG = ControlConfig(
    torque_scale=0.35,
    deadband=15.0,
    speed_max=50,
    smooth_alpha=0.35,
    stale_sendcan_sec=0.5,
)


# ── Test 1: Speed clamp boundary with live config ──

def test_speed_clamp_boundary_sweep():
    """Every possible TORQUE_CMD [-500..500] maps to speed within [-50, 50]."""
    for t in range(-500, 501):
        sl, sr = map_torques_to_speed_pair(float(t), float(t), LIVE_CFG)
        assert -50 <= sl <= 50, f"torque={t} -> SPD_L={sl} out of [-50,50]"
        assert -50 <= sr <= 50, f"torque={t} -> SPD_R={sr} out of [-50,50]"


def test_zero_torque_maps_to_zero():
    """Torque=0 maps to speed=0 (stopped)."""
    sl, sr = map_torques_to_speed_pair(0.0, 0.0, LIVE_CFG)
    assert sl == 0
    assert sr == 0


def test_deadband_maps_to_zero():
    """Torque below deadband (abs < 15) maps to speed=0."""
    for t in [-14, -10, -1, 0, 1, 10, 14]:
        sl, sr = map_torques_to_speed_pair(float(t), float(t), LIVE_CFG)
        assert sl == 0, f"torque={t} should be deadbanded to 0, got speed={sl}"
        assert sr == 0, f"torque={t} should be deadbanded to 0, got speed={sr}"


def test_above_deadband_moves():
    """Torque at or above deadband produces non-zero speed."""
    sl, sr = map_torques_to_speed_pair(15.0, 15.0, LIVE_CFG)
    assert sl > 0, f"torque=15 (at deadband) should move forward, got speed={sl}"
    sl, sr = map_torques_to_speed_pair(-15.0, -15.0, LIVE_CFG)
    assert sl < 0, f"torque=-15 should move backward, got speed={sl}"


# ── Test 2: Stale sendcan safety ──

def test_stale_sendcan_triggers_after_threshold():
    """sendcan_is_stale returns True after 0.5s gap."""
    assert not sendcan_is_stale(100.0, 99.6, 0.5)
    assert not sendcan_is_stale(100.0, 99.51, 0.5)
    assert sendcan_is_stale(100.0, 99.5, 0.5)
    assert sendcan_is_stale(100.0, 99.0, 0.5)


def test_stale_forces_zero_speed():
    """When stale, force_neutral=True produces speed=0."""
    sl, sr = map_torques_to_speed_pair(500.0, 500.0, LIVE_CFG, force_neutral=True)
    assert sl == 0
    assert sr == 0


def test_stale_with_bias_clamps_correctly():
    """Neutral + bias still stays within clamp range."""
    cfg = ControlConfig(
        torque_scale=0.35, deadband=15.0,
        speed_max=50,
        bias_l=100, bias_r=-100,
    )
    sl, sr = map_torques_to_speed_pair(0.0, 0.0, cfg, force_neutral=True)
    assert -50 <= sl <= 50
    assert -50 <= sr <= 50


# ── Test 3: PID torque ramp simulation ──

MAX_TORQUE = 500
MAX_TORQUE_RATE = 50
SPEED_FROM_RPM = 0.008587


def body_deadband_filter(torque, deadband=10):
    if torque > 0:
        torque += deadband
    else:
        torque -= deadband
    return torque


def simulate_body_pid(n_frames, speed_desired, speed_l_fn):
    """Simulate the body CarController PID for n_frames.

    speed_l_fn(frame) returns the SPEED_L/R feedback for that frame.
    Returns list of (torque_l, torque_r) per frame.
    """
    k_p, k_i = 110.0, 11.5
    i_rate = 1.0 / 100.0

    p_speed = 0.0
    i_speed = 0.0
    torque_l_filtered = 0.0
    torque_r_filtered = 0.0

    history = []
    for frame in range(n_frames):
        speed_l = speed_l_fn(frame)
        speed_r = speed_l
        speed_measured = SPEED_FROM_RPM * (speed_l + speed_r) / 2.0

        speed_error = speed_desired - speed_measured
        p_speed = speed_error * k_p
        i_speed = i_speed + speed_error * k_i * i_rate

        torque = p_speed + i_speed

        torque_l = torque
        torque_r = torque

        torque_l_filtered = np.clip(
            body_deadband_filter(torque_l, 10),
            torque_l_filtered - MAX_TORQUE_RATE,
            torque_l_filtered + MAX_TORQUE_RATE,
        )
        torque_r_filtered = np.clip(
            body_deadband_filter(torque_r, 10),
            torque_r_filtered - MAX_TORQUE_RATE,
            torque_r_filtered + MAX_TORQUE_RATE,
        )
        tl = int(np.clip(torque_l_filtered, -MAX_TORQUE, MAX_TORQUE))
        tr = int(np.clip(torque_r_filtered, -MAX_TORQUE, MAX_TORQUE))
        history.append((tl, tr))
    return history


def test_pid_ramp_from_standstill():
    """PID ramps torque gradually from standstill (rate limited at 50/frame)."""
    speed_desired = 0.6 / 5.0
    history = simulate_body_pid(50, speed_desired, lambda _: 0.0)

    for i, (tl, tr) in enumerate(history):
        assert -MAX_TORQUE <= tl <= MAX_TORQUE, f"frame {i}: tl={tl} exceeds +-500"
        assert -MAX_TORQUE <= tr <= MAX_TORQUE, f"frame {i}: tr={tr} exceeds +-500"
        assert tl == tr, f"frame {i}: straight line should have tl==tr"

    assert history[0][0] > 0, "First frame torque should be positive (forward)"

    for i in range(1, len(history)):
        delta = abs(history[i][0] - history[i - 1][0])
        assert delta <= MAX_TORQUE_RATE, f"frame {i}: rate {delta} > {MAX_TORQUE_RATE}"

    history_long = simulate_body_pid(2000, speed_desired, lambda _: 0.0)
    assert history_long[-1][0] > history_long[0][0], \
        "Torque should increase over 2000 frames due to integrator windup"


def test_pid_ramp_values_at_key_frames():
    """Spot-check torque at frames 0 and with longer runs for integrator windup."""
    speed_desired = 0.12
    history = simulate_body_pid(50, speed_desired, lambda _: 0.0)

    assert 20 <= history[0][0] <= 30, f"frame 0: got {history[0][0]}, expected ~23"
    assert 20 <= history[49][0] <= 30, f"frame 49: got {history[49][0]}, expected ~23-24"

    history_long = simulate_body_pid(5000, speed_desired, lambda _: 0.0)
    assert history_long[-1][0] > 50, \
        f"frame 4999: got {history_long[-1][0]}, expected >50 with integrator windup"


# ── Test 4: Synthetic speed feedback convergence ──

def test_feedback_convergence():
    """PID + synthetic speed feedback converges (doesn't oscillate or peg at +-500)."""
    speed_desired = 0.12
    est_speed = 0.0
    alpha_est = 0.1

    k_p, k_i = 110.0, 11.5
    i_rate = 1.0 / 100.0
    p_speed = 0.0
    i_speed = 0.0
    torque_l_filtered = 0.0

    torque_history = []
    error_history = []

    for frame in range(200):
        speed_measured = SPEED_FROM_RPM * est_speed

        speed_error = speed_desired - speed_measured
        error_history.append(abs(speed_error))
        p_speed = speed_error * k_p
        i_speed = i_speed + speed_error * k_i * i_rate

        torque = p_speed + i_speed
        torque_l_filtered = np.clip(
            body_deadband_filter(torque, 10),
            torque_l_filtered - MAX_TORQUE_RATE,
            torque_l_filtered + MAX_TORQUE_RATE,
        )
        tl = int(np.clip(torque_l_filtered, -MAX_TORQUE, MAX_TORQUE))
        torque_history.append(tl)

        sl, _ = map_torques_to_speed_pair(float(tl), float(tl), LIVE_CFG)
        est_speed = alpha_est * float(sl) + (1.0 - alpha_est) * est_speed

    assert torque_history[-1] < MAX_TORQUE, \
        f"Final torque={torque_history[-1]} should be < 500 with feedback"

    assert error_history[-1] < error_history[5], \
        f"Error should decrease: start={error_history[5]:.4f} end={error_history[-1]:.4f}"

    last20 = torque_history[-20:]
    spread = max(last20) - min(last20)
    assert spread < 100, f"Torque spread in last 20 frames = {spread}, expected < 100 (stable)"


# ── Test 5: Smoothing step response ──

def test_smoothing_step_response():
    """With smooth_alpha=0.35, measure steps to reach within 2 of target."""
    smoother = SpeedSmoother(0.35)
    target = 50
    steps_to_converge = None
    for i in range(100):
        result, _ = smoother.step(target, target)
        if abs(result - target) <= 2 and steps_to_converge is None:
            steps_to_converge = i + 1

    assert steps_to_converge is not None, "Smoother never converged to within 2 of target"
    assert steps_to_converge <= 15, \
        f"Took {steps_to_converge} steps to converge (>150ms at 100Hz), too slow"
    assert steps_to_converge >= 2, \
        f"Converged in {steps_to_converge} steps, smoothing is not doing anything"


def test_smoothing_doesnt_overshoot():
    """Smoother should never exceed the target value."""
    smoother = SpeedSmoother(0.35)
    for _ in range(50):
        result, _ = smoother.step(50, 50)
        assert result <= 50, f"Smoother overshot: {result} > 50"


# ── Test 6: Full-loop convergence with tuned parameters ──

TUNED_CFG = ControlConfig(
    torque_scale=2.0,
    deadband=15.0,
    speed_min=8,
    speed_max=100,
    smooth_alpha=0.5,
    stale_sendcan_sec=0.5,
)

MOTOR_STALL_THRESHOLD = 30


def simulate_full_loop(n_frames, joystick_accel, bridge_cfg, feedback_alpha=0.15):
    """Simulate body PID -> bridge control map -> feedback EMA -> CarState -> PID.

    Returns (speed_history, torque_history) where speed_history is the motor
    command (signed int) per frame.
    """
    k_p, k_i = 110.0, 11.5
    i_rate = 1.0 / 100.0

    speed_desired = (4.0 * joystick_accel) / 5.0

    i_speed = 0.0
    torque_l_filtered = 0.0
    est_speed = 0.0
    smoother = SpeedSmoother(bridge_cfg.smooth_alpha)

    speed_history = []
    torque_history = []

    for _ in range(n_frames):
        speed_measured = SPEED_FROM_RPM * est_speed
        speed_error = speed_desired - speed_measured

        p_speed = speed_error * k_p
        i_speed = i_speed + speed_error * k_i * i_rate

        torque = p_speed + i_speed
        torque_l_filtered = np.clip(
            body_deadband_filter(torque, 10),
            torque_l_filtered - MAX_TORQUE_RATE,
            torque_l_filtered + MAX_TORQUE_RATE,
        )
        tl = int(np.clip(torque_l_filtered, -MAX_TORQUE, MAX_TORQUE))
        torque_history.append(tl)

        sl, _ = map_torques_to_speed_pair(float(tl), float(tl), bridge_cfg)
        sl_smooth, _ = smoother.step(sl, sl)
        speed_history.append(sl_smooth)

        est_speed = feedback_alpha * float(sl_smooth) + (1.0 - feedback_alpha) * est_speed

    return speed_history, torque_history


def test_tuned_params_converge_above_stall():
    """With tuned params (accel=0.5), converged speed exceeds motor stall threshold."""
    speeds, torques = simulate_full_loop(500, joystick_accel=0.5, bridge_cfg=TUNED_CFG)

    final_speed = speeds[-1]
    assert final_speed > MOTOR_STALL_THRESHOLD, \
        f"Converged speed={final_speed}, must exceed stall threshold={MOTOR_STALL_THRESHOLD}"
    assert final_speed < 100, \
        f"Converged speed={final_speed}, should not be runaway (>100)"

    last20 = speeds[-20:]
    spread = max(last20) - min(last20)
    assert spread < 10, \
        f"Speed spread in last 20 frames = {spread}, expected < 10 (stable)"


def test_tuned_params_torque_bounded():
    """Torque stays within [-500, 500] throughout the simulation."""
    _, torques = simulate_full_loop(500, joystick_accel=0.5, bridge_cfg=TUNED_CFG)
    for i, tl in enumerate(torques):
        assert -MAX_TORQUE <= tl <= MAX_TORQUE, f"frame {i}: torque={tl} out of bounds"


def test_old_params_too_slow():
    """Confirm that the OLD parameters produce speed below stall (documents the problem)."""
    speeds, _ = simulate_full_loop(500, joystick_accel=0.15, bridge_cfg=LIVE_CFG, feedback_alpha=0.1)
    final_speed = speeds[-1]
    assert final_speed < MOTOR_STALL_THRESHOLD, \
        f"Old config should converge below stall: got speed={final_speed}"


# ── Test 7: Differential arc turning (forward + steer) ──

MAX_TURN_INTEGRATOR = 0.1


def simulate_full_loop_2axis(n_frames, joystick_accel, joystick_steer,
                              bridge_cfg, feedback_alpha=0.15):
    """Simulate both speed PID and turn PID through the bridge.

    Returns (speed_l_history, speed_r_history, torque_l_history, torque_r_history).
    """
    k_p, k_i = 110.0, 11.5
    i_rate = 1.0 / 100.0

    speed_desired = (4.0 * joystick_accel) / 5.0
    speed_diff_desired = -(joystick_steer) / 2.0

    i_speed = 0.0
    i_turn = 0.0
    torque_l_filtered = 0.0
    torque_r_filtered = 0.0
    est_speed_l = 0.0
    est_speed_r = 0.0
    smoother = SpeedSmoother(bridge_cfg.smooth_alpha)

    speed_l_hist, speed_r_hist = [], []
    torque_l_hist, torque_r_hist = [], []

    for _ in range(n_frames):
        fl = est_speed_l
        fr = est_speed_r
        speed_measured = SPEED_FROM_RPM * (fl + fr) / 2.0
        speed_diff_measured = SPEED_FROM_RPM * (fl - fr)

        speed_error = speed_desired - speed_measured
        p_speed = speed_error * k_p
        i_speed = i_speed + speed_error * k_i * i_rate
        torque = p_speed + i_speed

        turn_error = speed_diff_measured - speed_diff_desired
        freeze = ((turn_error < 0 and i_turn <= -MAX_TURN_INTEGRATOR) or
                  (turn_error > 0 and i_turn >= MAX_TURN_INTEGRATOR))
        if not freeze:
            i_turn = i_turn + turn_error * k_i * i_rate
        p_turn = turn_error * k_p
        torque_diff = p_turn + i_turn

        raw_tl = torque - torque_diff
        raw_tr = torque + torque_diff

        torque_l_filtered = np.clip(
            body_deadband_filter(raw_tl, 10),
            torque_l_filtered - MAX_TORQUE_RATE,
            torque_l_filtered + MAX_TORQUE_RATE,
        )
        torque_r_filtered = np.clip(
            body_deadband_filter(raw_tr, 10),
            torque_r_filtered - MAX_TORQUE_RATE,
            torque_r_filtered + MAX_TORQUE_RATE,
        )
        tl = int(np.clip(torque_l_filtered, -MAX_TORQUE, MAX_TORQUE))
        tr = int(np.clip(torque_r_filtered, -MAX_TORQUE, MAX_TORQUE))
        torque_l_hist.append(tl)
        torque_r_hist.append(tr)

        sl, sr = map_torques_to_speed_pair(float(tl), float(tr), bridge_cfg)
        sl_s, sr_s = smoother.step(sl, sr)
        speed_l_hist.append(sl_s)
        speed_r_hist.append(sr_s)

        est_speed_l = feedback_alpha * float(sl_s) + (1.0 - feedback_alpha) * est_speed_l
        est_speed_r = feedback_alpha * float(sr_s) + (1.0 - feedback_alpha) * est_speed_r

    return speed_l_hist, speed_r_hist, torque_l_hist, torque_r_hist


def test_arc_forward_right_uses_n4_differential():
    """Forward + right steer produces two POSITIVE speeds (N=4 path, not N=3 pivot)."""
    sl_h, sr_h, _, _ = simulate_full_loop_2axis(
        500, joystick_accel=0.5, joystick_steer=1.0, bridge_cfg=TUNED_CFG)

    final_sl = sl_h[-1]
    final_sr = sr_h[-1]

    assert final_sl > 0 and final_sr > 0, \
        f"Arc should have both speeds positive (N=4 differential): sl={final_sl} sr={final_sr}"
    assert final_sl != final_sr, \
        f"Arc should have different speeds: sl={final_sl} sr={final_sr}"
    assert min(final_sl, final_sr) >= 10, \
        f"Slower wheel speed={min(final_sl, final_sr)} should be above ~10 to produce motion"


def test_arc_forward_right_faster_wheel_above_stall():
    """The faster wheel in a forward+right arc exceeds motor stall threshold."""
    sl_h, sr_h, _, _ = simulate_full_loop_2axis(
        500, joystick_accel=0.5, joystick_steer=1.0, bridge_cfg=TUNED_CFG)

    faster = max(sl_h[-1], sr_h[-1])
    assert faster > MOTOR_STALL_THRESHOLD, \
        f"Faster wheel speed={faster}, must exceed stall threshold={MOTOR_STALL_THRESHOLD}"


def test_arc_forward_left_mirrors_right():
    """Forward + left steer mirrors forward + right (symmetric)."""
    sl_r, sr_r, _, _ = simulate_full_loop_2axis(
        500, joystick_accel=0.5, joystick_steer=1.0, bridge_cfg=TUNED_CFG)
    sl_l, sr_l, _, _ = simulate_full_loop_2axis(
        500, joystick_accel=0.5, joystick_steer=-1.0, bridge_cfg=TUNED_CFG)

    assert abs(sl_r[-1] - sr_l[-1]) <= 2, \
        f"Left-arc slow wheel should match right-arc slow wheel: {sl_r[-1]} vs {sr_l[-1]}"
    assert abs(sr_r[-1] - sl_l[-1]) <= 2, \
        f"Left-arc fast wheel should match right-arc fast wheel: {sr_r[-1]} vs {sl_l[-1]}"


def test_pivot_turn_with_steer_max_1():
    """Pure pivot (accel=0, steer=1.0) produces speeds above threshold with steer_max=1.0."""
    sl_h, sr_h, _, _ = simulate_full_loop_2axis(
        500, joystick_accel=0.0, joystick_steer=1.0, bridge_cfg=TUNED_CFG)

    final_sl = sl_h[-1]
    final_sr = sr_h[-1]

    assert final_sl * final_sr <= 0, \
        f"Pivot should have opposite-sign speeds: sl={final_sl} sr={final_sr}"

    pivot_speed = max(abs(final_sl), abs(final_sr))
    assert pivot_speed >= 15, \
        f"Pivot speed={pivot_speed}, should be >= 15 for visible motion"


def test_arc_torques_bounded():
    """All torques in a forward+steer arc stay within [-500, 500]."""
    _, _, tl_h, tr_h = simulate_full_loop_2axis(
        500, joystick_accel=0.5, joystick_steer=1.0, bridge_cfg=TUNED_CFG)
    for i, (tl, tr) in enumerate(zip(tl_h, tr_h)):
        assert -MAX_TORQUE <= tl <= MAX_TORQUE, f"frame {i}: torque_l={tl} out of bounds"
        assert -MAX_TORQUE <= tr <= MAX_TORQUE, f"frame {i}: torque_r={tr} out of bounds"


# ── Test 8: Speed dead zone kills idle buzz ──

def test_speed_min_zeros_idle_buzz():
    """CarController sends ±10 at idle; with deadband=15 + speed_min=8, bridge outputs 0."""
    for idle_torque in [-10, -5, 0, 5, 10]:
        sl, sr = map_torques_to_speed_pair(float(idle_torque), float(idle_torque), TUNED_CFG)
        assert sl == 0, f"torque={idle_torque} should produce speed 0, got sl={sl}"
        assert sr == 0, f"torque={idle_torque} should produce speed 0, got sr={sr}"


def test_speed_min_passes_real_commands():
    """Torques well above deadband still produce non-zero motor speed."""
    sl, sr = map_torques_to_speed_pair(50.0, 50.0, TUNED_CFG)
    assert sl > 0, f"torque=50 should produce positive speed, got sl={sl}"
    assert sr > 0, f"torque=50 should produce positive speed, got sr={sr}"


def test_speed_min_no_effect_without_setting():
    """With speed_min=0 (default), small speeds pass through."""
    cfg_no_min = ControlConfig(torque_scale=1.0, deadband=0.0, speed_min=0)
    sl, sr = map_torques_to_speed_pair(5.0, 5.0, cfg_no_min)
    assert sl != 0 or sr != 0, "Without speed_min, small torques should produce non-zero speed"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
