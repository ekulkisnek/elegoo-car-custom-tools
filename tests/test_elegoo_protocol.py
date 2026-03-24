from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.elegoo_protocol import (
    Direction,
    MotorDirection,
    MotorSelection,
    RockerDirection,
    cmd_car_timed,
    cmd_car_untimed,
    cmd_motor_control,
    cmd_motor_speed,
    cmd_rocker,
    cmd_stop,
)


class ProtocolCommandTests(unittest.TestCase):
    def parse(self, frame: str) -> dict[str, object]:
        self.assertTrue(frame.startswith("{"))
        self.assertTrue(frame.endswith("}"))
        return json.loads(frame)

    def test_stop_frame(self) -> None:
        self.assertEqual(cmd_stop(), '{"N":100}')

    def test_car_timed_frame(self) -> None:
        payload = self.parse(cmd_car_timed(Direction.FORWARD, 80, 450))
        self.assertEqual(payload["N"], 2)
        self.assertEqual(payload["D1"], 3)
        self.assertEqual(payload["D2"], 80)
        self.assertEqual(payload["T"], 450)
        self.assertIn("H", payload)

    def test_car_untimed_frame(self) -> None:
        payload = self.parse(cmd_car_untimed(Direction.LEFT, 55))
        self.assertEqual(payload["N"], 3)
        self.assertEqual(payload["D1"], 1)
        self.assertEqual(payload["D2"], 55)

    def test_motor_control_frame(self) -> None:
        payload = self.parse(cmd_motor_control(MotorSelection.RIGHT_A, MotorDirection.BACKWARD, 33))
        self.assertEqual(payload["N"], 1)
        self.assertEqual(payload["D1"], 1)
        self.assertEqual(payload["D2"], 33)
        self.assertEqual(payload["D3"], 2)

    def test_motor_speed_frame(self) -> None:
        payload = self.parse(cmd_motor_speed(25, 100))
        self.assertEqual(payload["N"], 4)
        self.assertEqual(payload["D1"], 25)
        self.assertEqual(payload["D2"], 100)

    def test_rocker_frame(self) -> None:
        payload = self.parse(cmd_rocker(RockerDirection.LEFT_FORWARD))
        self.assertEqual(payload["N"], 102)
        self.assertEqual(payload["D1"], 5)


if __name__ == "__main__":
    unittest.main()
