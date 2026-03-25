#!/usr/bin/env python3
"""
Set params so openpilot skips onboarding and is ready for body engagement:
  - HasAcceptedTerms / CompletedTrainingVersion (skip UI onboarding)
  - OpenpilotEnabledToggle (required for card to enable controller)
  - CalibrationParams (valid calibration blob so calibrationd is happy)

Run from repo with openpilot venv:
  cd openpilot && source .venv/bin/activate && export PYTHONPATH=\"$PWD\" && \\
  python3 ../scripts/stage-b-verify/openpilot_skip_onboarding.py
"""
from __future__ import annotations

import os
import sys


def main() -> int:
  root = os.environ.get("OPENPILOT_ROOT")
  if root:
    sys.path.insert(0, os.path.abspath(root))
  else:
    here = os.path.dirname(os.path.abspath(__file__))
    guess = os.path.normpath(os.path.join(here, "..", "..", "openpilot"))
    if os.path.isdir(guess):
      sys.path.insert(0, guess)

  from cereal import messaging
  from openpilot.common.params import Params
  from openpilot.system.version import terms_version, training_version

  p = Params()

  p.put("HasAcceptedTerms", terms_version)
  p.put("CompletedTrainingVersion", training_version)
  print(f"HasAcceptedTerms={terms_version!r}")
  print(f"CompletedTrainingVersion={training_version!r}")

  p.put_bool("OpenpilotEnabledToggle", True)
  print("OpenpilotEnabledToggle=True")

  msg = messaging.new_message('liveCalibration')
  msg.liveCalibration.validBlocks = 20
  msg.liveCalibration.rpyCalib = [0.0, 0.0, 0.0]
  p.put("CalibrationParams", msg.to_bytes())
  print("CalibrationParams set (validBlocks=20, rpyCalib=[0,0,0])")

  print("OK — params ready for body engagement.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
