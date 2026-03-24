# Stage D — openpilot moving wheels (done)

**Milestone:** openpilot is driving **wheel / motor** output through your stack for Stage D (synthetic CAN / bridge path), independent of a full comma production pipeline.

**This note is about log noise, not blockers.** The following classes of message are **usually not Stage D blockers** — they reflect macOS dev, incomplete model/native builds, or upstream “dirty tree” checks rather than the ELEGOO **TCP bridge** to the car.

---

## What each class of message usually means (not Stage D blockers)

| Symptom | Likely cause |
|---------|----------------|
| `…: needs update` | openpilot’s **“dirty files” / version check** — your tree differs from what it expects. Annoying, not specific to the bridge. |
| `missing public key` | **Signing / comma key material** — dev noise unless you care about official releases. |
| `objc … Class AVFFrameReceiver … both … av … and … cv2` | **PyAV** and **OpenCV** both ship **libav**; duplicate Objective-C classes on **macOS**. Can cause weird crashes; not the ELEGOO TCP bridge. |
| `Failed to connect to system D-Bus` / `wifi_manager` errors | UI expects **Linux NetworkManager** over D-Bus. **macOS has no system bus** — expected on Mac dev. |
| `Assertion failed: (handle) … ekf_load.cc` | **EKF** / calibration **asset or load path** problem — localization/calibration path, not the motor bridge. |
| `FileNotFoundError: … dmonitoring_model_metadata.pkl` / `driving_vision_metadata.pkl` | Vision / driver monitoring **model metadata** not present (not downloaded or not built). **modeld** / **dmonitoringmodeld** crash → no full driving model pipeline → strong contributor to **“unavailable”**. |
| `encoderd … FileNotFoundError: [Errno 2] No such file or directory (exec)` | Native **encoderd** binary likely **missing or wrong path** (incomplete **scons** build for that target on Mac). |
| `Waiting for CAN messages…` | Normal while the stack waits for CAN traffic; your bridge supplies **synthetic CAN** when it’s running. |
| **loggerd / camera rotation** | Already documented elsewhere as **non-blocker** for Stage D. |

---

## Related

- **`openpilot-mods/`** — local patches for camera / manager / UI on Mac (`stage-b-openpilot-camera.patch`).
- **`docs/STAGE_B_CAMERA_OPENPILOT.md`** — camera visible in openpilot UI.
- **`docs/MAC_CONTROLS_CAR.md`** — Mac → TCP/100 → Serial2 → UNO (ELEGOO path).
