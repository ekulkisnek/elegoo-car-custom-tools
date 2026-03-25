#!/usr/bin/env bash
# Stage E control map tests + Stage D bridge tests + plumbing smoke.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OP="${OPENPILOT_ROOT:-$ROOT/openpilot}"
cd "$OP"
# shellcheck source=/dev/null
source .venv/bin/activate
export PYTHONPATH="$PWD:$PWD/rednose_repo:$ROOT/elegoo-car-custom-tools/scripts"
export PYTHONUNBUFFERED=1

echo "=== pytest: Stage E (control map) ==="
pytest -q --tb=short "$ROOT/scripts/stage-e-verify/test_stage_e_control.py"

echo "=== pytest: sendcan stale + bridge integration ==="
pytest -q --tb=short "$ROOT/scripts/stage-d-verify/test_sendcan_stale_and_bridge.py"

echo "=== pytest: Stage D (bridge) ==="
pytest -q --tb=short "$ROOT/scripts/stage-d-verify/test_stage_d_bridge.py"

echo "=== pytest: engagement chain + Stage F feedback ==="
pytest -q --tb=short "$ROOT/scripts/stage-e-verify/test_engagement_chain.py"

echo "=== plumbing smoke (0.5s) ==="
python3 "$ROOT/elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py" --mode plumbing --duration 0.5

echo "=== Stage E automated verify: PASS ==="
