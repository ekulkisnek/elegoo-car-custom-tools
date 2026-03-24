# Agent Notes

## 2026-03-24 1

- Goal: create a guided motor test suite that is evidence-backed by the stock firmware and observable by the user during real runs.
- Design constraint: no firmware changes; tests must speak the existing TCP `:100` JSON protocol.

## 2026-03-24 2

- Verified motor-control entry points in the UNO app firmware:
  - `N=1` -> `CMD_MotorControl_xxx0`
  - `N=2` -> `CMD_CarControlTimeLimit_xxx0`
  - `N=3` -> `CMD_CarControlNoTimeLimit_xxx0`
  - `N=4` -> `CMD_MotorControlSpeed_xxx0`
  - `N=102` -> rocker-mode control
  - `N=100` -> standby and stop

## 2026-03-24 3

- Important movement semantics from source:
  - `N=3` direction mapping is not the same numbering as the rocker enum names in the source comments:
    - `D1=1` -> left
    - `D1=2` -> right
    - `D1=3` -> forward
    - `D1=4` -> backward
  - `N=1` motor selection:
    - `D1=0` both motors
    - `D1=1` motor A only
    - `D1=2` motor B only
  - Driver comments label motor A as `Right` and motor B as `Left`.
  - `N=4` sets both motors forward with independent PWM values.

## 2026-03-24 4

- Test strategy chosen:
  - local unit tests for command encoding
  - dry-run mode for visible command plans without hardware
  - interactive real-run mode for physical observation and operator confirmation
  - session JSON logs to preserve what was sent and what the operator saw

## 2026-03-24 5

- Heartbeat handling added to the real-run client because the ESP32 bridge disconnects after missed `{Heartbeat}` replies.
- The client records all inbound frames so later debugging can compare observed motor behavior with any returned acknowledgements or heartbeats.

## 2026-03-24 6

- Local verification completed:
  - `python3 -m unittest discover -s elegoo-car-custom-tools/tests -p 'test_*.py'` -> 6 tests passed
  - `python3 elegoo-car-custom-tools/scripts/elegoo_motor_test_suite.py --dry-run --non-interactive` -> completed and wrote a session log under `output/motor-tests`
- No live-car run was executed in this turn, so physical-motion success is still pending operator validation.
