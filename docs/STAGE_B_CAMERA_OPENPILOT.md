# Stage B — Camera works in openpilot (milestone)

**Goal:** Webcam / MJPEG camera preview is usable in **openpilot UI** on dev setups (e.g. **macOS**, **USE_WEBCAM**, no Panda / ESP32-style sources) without misleading overlays blocking the image.

**Status:** **DONE** — all local changes are captured under **`openpilot-mods/`** (patch + README), not the full commaai tree.

---

## Files touched (5)

| Path | Role |
|------|------|
| `system/manager/process_config.py` | `webcamerad_gate()` + **`OPENPILOT_WEBCAM_ALWAYS=1`** so **webcamerad** can run without toggling driver view. |
| `system/manager/helpers.py` | **`OPENPILOT_SKIP_UNBLOCK_STDOUT=1`** skips **`forkpty`** in **`unblock_stdout`** (macOS + GUI libs). |
| `selfdrive/ui/layouts/main.py` | **`OPENPILOT_START_ONROAD=1`** → jump to **onroad** after onboarding. |
| `selfdrive/ui/mici/layouts/main.py` | Same: scroll to **onroad** on first setup when env set. |
| `selfdrive/ui/mici/onroad/augmented_road_view.py` | **`NOBOARD`** or **`USE_WEBCAM`**: clear “system booting” when Panda is unknown; **skip** dark overlay + offroad label so **MJPEG preview** is visible. |

---

## Environment variables (typical)

```bash
export USE_WEBCAM=1
export OPENPILOT_WEBCAM_ALWAYS=1
export OPENPILOT_START_ONROAD=1
export OPENPILOT_SKIP_UNBLOCK_STDOUT=1
# optional: hide Panda-unknown / overlay behavior in AugmentedRoadView
export NOBOARD=1
```

---

## Apply patch

Upstream SHA: **`openpilot-mods/BASE_COMMIT.txt`**.

```bash
git -C "$OPENPILOT_ROOT" apply "$(pwd)/openpilot-mods/patches/stage-b-openpilot-camera.patch"
```

See **`openpilot-mods/README.md`** for full detail.
