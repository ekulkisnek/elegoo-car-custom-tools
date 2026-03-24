# openpilot — local mods (camera / macOS dev)

This folder **does not** vendor [commaai/openpilot](https://github.com/commaai/openpilot). It only records **our patches** so they can be reapplied on top of a clean checkout.

## Upstream revision tested

See **`BASE_COMMIT.txt`** (full git SHA). Apply the patch **on that commit** (or expect manual conflict resolution if upstream moved).

## Patch

| File | Purpose |
|------|--------|
| `patches/OPENPILOT_CONFIRMED_SHOWING_CAMERA.patch` | Unified diff for all changes below |

## What the patch does (technical)

1. **`OPENPILOT_WEBCAM_ALWAYS=1`** — `process_config.py` adds `webcamerad_gate()`: when set, **webcamerad** is always allowed to run (same as “driver view” on) without toggling UI, so **MJPEG / webcam path** stays up for dev.
2. **`USE_WEBCAM`** — unchanged: still enables the `webcamerad` process when unset `WEBCAM` logic applies; the gate layers on top.
3. **`OPENPILOT_START_ONROAD=1`** — **UI layouts** (`main.py` and **mici** `main.py`): after onboarding, jump straight to **onroad** layout so the **camera preview** is visible without extra navigation.
4. **`OPENPILOT_SKIP_UNBLOCK_STDOUT=1`** — **`helpers.unblock_stdout`**: skip the **forkpty** path on **macOS** when native GUI libs (e.g. raylib) are already loaded — avoids **unsafe fork** behavior during manager startup.

## Apply

From your **openpilot** repo root (clean tree or stash first):

```bash
git apply /path/to/elegoo-car-custom-tools/openpilot-mods/patches/OPENPILOT_CONFIRMED_SHOWING_CAMERA.patch
```

Or from this repo:

```bash
git -C "$OPENPILOT_ROOT" apply "$(pwd)/openpilot-mods/patches/OPENPILOT_CONFIRMED_SHOWING_CAMERA.patch"
```

## Typical dev env (example)

```bash
export USE_WEBCAM=1
export OPENPILOT_WEBCAM_ALWAYS=1
export OPENPILOT_START_ONROAD=1
export OPENPILOT_SKIP_UNBLOCK_STDOUT=1
# then launch openpilot per your usual flow (e.g. manager / UI)
```

Adjust to match your install; not all variables are required for every test.
