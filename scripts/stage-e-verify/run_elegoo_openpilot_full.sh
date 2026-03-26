#!/usr/bin/env bash
# Unified launcher: bridge → manager → optional joystick.
#
# Usage (software-only, no car):
#   cd /Users/lukekensik/coding/elegoo-comma-1
#   ./scripts/stage-e-verify/run_elegoo_openpilot_full.sh
#
# Usage (live with car):
#   export CAR_IP=192.168.1.191
#   ./scripts/stage-e-verify/run_elegoo_openpilot_full.sh --live
#
# Usage (with keyboard joystick):
#   ./scripts/stage-e-verify/run_elegoo_openpilot_full.sh --joystick
#
# Ctrl+C stops everything (bridge sends N=100 stop on exit).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OP="${OPENPILOT_ROOT:-$ROOT/openpilot}"

MODE="dry-run"
JOYSTICK=""
EXTRA_BRIDGE_ARGS=""
for arg in "$@"; do
  case "$arg" in
    --live)    MODE="live" ;;
    --joystick) JOYSTICK="1" ;;
    *)         EXTRA_BRIDGE_ARGS="$EXTRA_BRIDGE_ARGS $arg" ;;
  esac
done

CAR_IP="${CAR_IP:-192.168.1.191}"

cleanup() {
  echo ""
  echo "[launcher] shutting down..."
  kill $BRIDGE_PID 2>/dev/null || true
  [ -n "${MANAGER_PID:-}" ] && kill $MANAGER_PID 2>/dev/null || true
  wait 2>/dev/null || true
  echo "[launcher] done."
}
trap cleanup EXIT INT TERM

cd "$OP"
# shellcheck source=/dev/null
source .venv/bin/activate
export PYTHONPATH="$PWD:$PWD/rednose_repo"
export PYTHONUNBUFFERED=1

# ── Step 1: Start bridge (publishes pandaStates + can before manager needs them) ──
echo "[launcher] starting bridge (mode=$MODE)..."

BRIDGE_CMD="python3 $ROOT/elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py --mode $MODE --log-every-n 100 --control-log"
if [ "$MODE" = "live" ]; then
  BRIDGE_CMD="$BRIDGE_CMD --tcp-host $CAR_IP --tcp-send-hz 15 --speed-max 100 --speed-min 8"
  if [ -n "$JOYSTICK" ]; then
    BRIDGE_CMD="$BRIDGE_CMD --joystick-direct"
  else
    BRIDGE_CMD="$BRIDGE_CMD --torque-scale 2.0 --deadband 15 --smooth-alpha 0.5 --feedback-alpha 0.4 --stale-sendcan-sec 0.5 --stale-sendcan-stop"
  fi
fi
BRIDGE_CMD="$BRIDGE_CMD $EXTRA_BRIDGE_ARGS"

$BRIDGE_CMD &
BRIDGE_PID=$!
echo "[launcher] bridge PID=$BRIDGE_PID"

# Give bridge time to establish messaging sockets
sleep 2

# ── Step 2: Start openpilot manager ──
echo "[launcher] starting openpilot manager..."

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export OPENPILOT_SKIP_UNBLOCK_STDOUT=1
export OPENPILOT_WEBCAM_ALWAYS=1
export USE_WEBCAM=1
export ROAD_CAM="${STREAM_URL:-http://${CAR_IP}:81/stream}"
export NOBOARD=1
export FINGERPRINT="COMMA_BODY"
export SKIP_FW_QUERY=1
export SIMULATION=1
export BLOCK="${BLOCK:-}${BLOCK:+,}encoderd,loggerd,logmessaged,manage_athenad,micd,modeld,dmonitoringmodeld,dmonitoringd,locationd,paramsd,stream_encoderd,radard,torqued,plannerd,lagd,feedbackd,soundd,webrtcd,bridge,webjoystick,controlsd"
export OPENPILOT_START_ONROAD=1

python3 "$ROOT/scripts/stage-b-verify/openpilot_skip_onboarding.py"

python3 -u system/manager/manager.py &
MANAGER_PID=$!
echo "[launcher] manager PID=$MANAGER_PID"

# ── Step 3: Optionally start joystick ──
if [ -n "$JOYSTICK" ]; then
  sleep 8
  echo "[launcher] starting keyboard joystick (foreground — WASD + ESC to quit)..."
  echo "[launcher] all processes running. Press ESC in joystick to stop."
  python3 "$ROOT/scripts/stage-e-verify/elegoo_joystick.py" --keyboard --accel 0.8 --steer-max 1.0
else
  echo "[launcher] all processes running. Ctrl+C to stop."
  wait $MANAGER_PID
fi
