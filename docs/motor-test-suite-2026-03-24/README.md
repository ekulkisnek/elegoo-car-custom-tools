# Motor Test Suite

This suite is for the stock ELEGOO TCP bridge on port `100`.

Files:

- [`elegoo_protocol.py`](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/scripts/elegoo_protocol.py): command builders for the stock JSON protocol.
- [`elegoo_motor_test_suite.py`](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/scripts/elegoo_motor_test_suite.py): guided terminal runner.
- [`test_elegoo_protocol.py`](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/tests/test_elegoo_protocol.py): local unit tests for command encoding.
- [`AGENT_NOTES.md`](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/docs/motor-test-suite-2026-03-24/AGENT_NOTES.md): evidence and design notes.

## What It Tests

The runner covers each distinct motion-control path found in the stock UNO firmware:

- `N=2`: timed car movement
- `N=3`: untimed car movement
- `N=102`: rocker-direction movement
- `N=1`: single-motor and both-motor direct control
- `N=4`: differential left/right PWM control
- `N=100`: stop and standby

## What You Can See

When you run the suite, the terminal shows:

- the exact JSON command being sent
- the expected vehicle motion
- the firmware basis for that expectation
- a prompt for whether the observed motion matched

Each session writes a JSON log under:

- [`output/motor-tests`](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/output/motor-tests)

That log records:

- every attempted test step
- every command string
- your verdict for each step
- any inbound TCP frames, including heartbeat traffic

## Safe First Run

Dry run only:

```bash
python3 elegoo-car-custom-tools/scripts/elegoo_motor_test_suite.py --dry-run
```

Local unit tests:

```bash
python3 -m unittest discover -s elegoo-car-custom-tools/tests -p 'test_*.py'
```

Real car session on the stock AP:

```bash
python3 elegoo-car-custom-tools/scripts/elegoo_motor_test_suite.py --host 192.168.4.1
```

## Recommended Physical Setup

- Put the car on the floor with clear space around it.
- Keep one hand near the power switch.
- Start with the default safe speeds in the suite.
- Watch for unexpected yaw in the single-motor tests; those are intended to reveal left/right motor identity.
