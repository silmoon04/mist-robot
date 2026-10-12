# Flashing LineageOS on the Mi 9 SE (`grus`) — plan & rescue kit

> Status: **PLAN ONLY — nothing here has been executed.** Do this deliberately, not in a hurry.
> Recommended ROM: **LineageOS 22.2 (Android 15), official** for `grus` (de-Googled out of the box).
> Runner-up: crDroid 12 (Android 16, unofficial).

## ⚠️ Read first — the three things that brick `grus`
1. **Anti-rollback (ARB):** never flash a stock fastboot ROM with a **lower** ARB index than what's on the phone → **permanent hard-brick**. Any rescue ROM must be ARB ≥ current.
2. **Mi unlock wait:** Xiaomi's Mi Unlock tool binds your Mi account and enforces a **~168 h (7-day) waiting period** (2025 policy: account ≥180 days old, 1 unlock/year). **No safe bypass** — third-party "instant unlock" tools brick/flag. Unlocking also **WIPES the phone.**
3. **Firmware base + encryption:** you must be on the **Android-11 firmware/vendor base** before flashing LOS 22.x (the #1 `grus` install failure), and you must **Format data** in recovery (MIUI→Lineage encryption mismatch) or it bootloops.

Back up everything off the phone first (it will be wiped at least twice).

## Rescue kit — download BEFORE you start
- **Stock fastboot ROM for grus** (ARB ≥ current) — for recovery via Mi Flash: https://xiaomirom.com/en/rom/mi-9-se-grus-global-fastboot-recovery-rom/
- **Mi Flash tool** (Windows) — flashes the fastboot ROM if anything goes wrong.
- **LineageOS recovery + ROM** for grus: https://wiki.lineageos.org/devices/grus/ · install: https://wiki.lineageos.org/devices/grus/install/ · downloads: https://download.lineageos.org/devices/grus
- **platform-tools** (already installed: `<LOCAL_HOME>\platform-tools`).
- EDL test-point (last-resort only): https://www.isppinout.com/2021/11/mi-9-se-edl-mode-test-point.html

## Steps
### 1. Unlock the bootloader (the 7-day part)
- Developer options: keep **USB debugging** + **OEM unlocking** on (already done), and tap **"Mi Unlock status" → add account & device** (binds your Mi account).
- Insert a SIM + mobile data on the phone (Xiaomi often requires this for binding).
- On Windows, run **miflash_unlock**, sign in, connect phone in **Fastboot** (power off → hold **Vol Down + Power**), click Unlock. It will tell you the wait (e.g. 168 h). Come back after the wait and unlock again → **this wipes the phone**.

### 2. Confirm firmware base = Android 11
- Stay on the current **MIUI 12.5 / Android 11** (you already are: `V12.5.1.0.RFBEUXM`). Good — no firmware downgrade/upgrade needed.

### 3. Flash LineageOS recovery
```sh
adb reboot bootloader
fastboot flash recovery lineage-22.2-<date>-recovery-grus.img
# do NOT let it boot to system yet:
fastboot reboot recovery     # or: Vol Up + Power immediately after disconnect
```

### 4. Format data + sideload the ROM
In LineageOS recovery:
- **Factory reset → Format data/factory reset** (clears encryption).
- **Apply update → Apply from ADB**, then on PC:
```sh
adb -d sideload lineage-22.2-<date>-nightly-grus-signed.zip
```
- (Optional) for a robot you likely want **NO GApps** (keep it de-Googled). If you ever need Play, sideload **MindTheGapps** for Android 15 in the same session *before* first boot.
- Reboot to system. First boot takes a few minutes.

## If it goes wrong
- **Bootloop / no system:** boot to fastboot (Vol Down + Power) → it's still recoverable.
- **Restore stock:** Mi Flash + the grus fastboot ROM, choose **"clean all"** (NOT "clean all and lock" — relocking an unlocked phone with a custom/empty system can hard-brick). Respect ARB (ROM ARB ≥ phone).
- **No fastboot either:** EDL 9008 via test point + the fastboot ROM (note: modern Xiaomi EDL may need an authorized account).

## After LineageOS — sensors for the robot
LineageOS exposes the same sensors (BMI160 IMU, AKM magnetometer, light, proximity, GPS). De-Googled means a sensor-streaming app must come from F-Droid or be sideloaded. Easiest robot path stays the same: an app pushing **UDP CSV (IMU/mag/GPS) over WiFi**, or USB via `adb reverse`, into the ESP32.
