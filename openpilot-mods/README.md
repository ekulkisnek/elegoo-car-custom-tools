# openpilot — local mods (camera / macOS dev)

This folder **does not** vendor [commaai/openpilot](https://github.com/commaai/openpilot). It only records **our patches** so they can be reapplied on top of a clean checkout.

## Upstream revision tested

See **`BASE_COMMIT.txt`** (full git SHA). Apply the patch **on that commit** (or expect manual conflict resolution if upstream moved).

## Patch (Stage B — current)

| File | Purpose |
|------|--------|
| **`patches/stage-b-openpilot-camera.patch`** | **Unified diff for all 5 files** (replaces the earlier 4-file snapshot). |

Legacy: commit **`OPENPILOT CONFIRMED SHOWING CAMERA`** used `OPENPILOT_CONFIRMED_SHOWING_CAMERA.patch` (4 files). **Stage B** adds **`augmented_road_view.py`** for unobstructed webcam preview when **`USE_WEBCAM`** / **`NOBOARD`**.

## What the patch does (technical)

1. **`OPENPILOT_WEBCAM_ALWAYS=1`** — `process_config.py` adds `webcamerad_gate()`: when set, **webcamerad** is always allowed to run (same as “driver view” on) without toggling UI, so **MJPEG / webcam path** stays up for dev.
2. **`USE_WEBCAM`** — must be set for the `webcamerad` process to be enabled at all (`enabled=WEBCAM`); the gate layers on top.
3. **`OPENPILOT_START_ONROAD=1`** — **UI layouts** (`main.py` and **mici** `main.py`): after onboarding, jump straight to **onroad** layout so the **camera preview** is visible without extra navigation.
4. **`OPENPILOT_SKIP_UNBLOCK_STDOUT=1`** — **`helpers.unblock_stdout`**: skip the **forkpty** path on **macOS** when native GUI libs (e.g. raylib) are already loaded — avoids **unsafe fork** behavior during manager startup.
5. **`augmented_road_view.py`** — **`_webcam_dev_mode()`** is true when **`NOBOARD=1`** or **`USE_WEBCAM`** is set: if Panda type is unknown, do **not** show **“system booting”**; when not onroad, **do not** draw the dark overlay / offroad label so the **camera image** is not covered (ESP32 / webcam dev without a comma device).

## Apply

From your **openpilot** repo root (clean tree or stash first):

```bash
git apply /path/to/elegoo-car-custom-tools/openpilot-mods/patches/stage-b-openpilot-camera.patch
```

Or from this repo:

```bash
git -C "$OPENPILOT_ROOT" apply "$(pwd)/openpilot-mods/patches/stage-b-openpilot-camera.patch"
```

## Typical dev env (example)

```bash
export USE_WEBCAM=1
export NOBOARD=1
export OPENPILOT_WEBCAM_ALWAYS=1
export OPENPILOT_START_ONROAD=1
export OPENPILOT_SKIP_UNBLOCK_STDOUT=1
# then launch openpilot per your usual flow (e.g. manager / UI)
```

Adjust to match your install; not all variables are required for every test.

## See also

- **`docs/STAGE_B_CAMERA_OPENPILOT.md`** — Stage B milestone summary.
