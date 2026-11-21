# WSL2 setup: UlixArm (`/dev/ttyACM0`), Meta Quest (adb), RealSense D405

WSL2 sees no USB devices by default. Each one is passed in from Windows with [usbipd-win](https://github.com/dorssel/usbipd-win),
and needs a udev rule so your user (not only root) can open it.

## 1. One-time setup

**WSL: turn on systemd** so udev runs and applies the rules below. Without it, every replug gives a root-only device.

```bash
printf '\n[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf
```

**WSL: udev rules** (2e88 = Ulix Power Box, 2833 = Meta Quest, 8086 = Intel RealSense):

```bash
sudo tee /etc/udev/rules.d/51-ulix-vr.rules <<'EOF'
SUBSYSTEM=="tty", ATTRS{idVendor}=="2e88", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="2e88", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="2833", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="8086", MODE="0666"
EOF
sudo usermod -aG dialout $USER
```

Then from Windows: `wsl --shutdown`, and reopen WSL. Check that `ps -p 1 -o comm=` prints `systemd`.

**Quest:** turn on Developer Mode in the Meta Horizon phone app (Devices → Headset settings → Developer mode).

**Windows (admin PowerShell):** install usbipd (`winget install usbipd`), plug everything in, and share each device once:

```powershell
usbipd list
usbipd bind --busid <BUSID>     # once per device; sharing survives reboots
```

Find the devices in `usbipd list` by VID:

| Device | VID:PID | Shows as |
|---|---|---|
| Ulix Power Box | `2e88:4603` | USB Serial Device (COMx) |
| Meta Quest 3S | `2833:50xx` | XRSP Interface, Crosswind Interface, ... |
| RealSense D405 | `8086:0b5b` | Intel RealSense ... (use a USB 3 port) |

## 2. Every session

**Windows (PowerShell).** Attaching is lost on every replug, sleep and reboot. `--auto-attach` re-attaches automatically, so leave
that window open:

```powershell
usbipd attach --wsl --busid <ARM_BUSID>
usbipd attach --wsl --busid <D405_BUSID>
usbipd attach --wsl --busid <QUEST_BUSID> --auto-attach    # the Quest re-enumerates often
```

**WSL.** Run each terminal after `source /home/ostif/ulixarm_vr/env.sh`:

```bash
python examples/00_check_env.py         # all OK? /dev/ttyACM0 present and writable
adb devices                             # Quest must say "device" (see Troubleshooting)
adb reverse tcp:8443 tcp:8443           # re-run after every Quest replug/sleep
```

```bash
# terminal 1
vr-teleop-relay
# terminal 2
bash examples/03_vr_teleoperate.sh      # or: CAM_SERIAL=<serial> bash examples/04_vr_record.sh
```

**Quest:** in the browser, open `http://localhost:8443/`. Tap **Calibrate wrist** (once), then **Start Teleop**, and accept the VR
prompt. **Stay in VR**: the page only streams controller data inside the immersive session. Taking the headset off or pressing
the Meta button pauses it.

Controls (right controller): **grip** = clutch (hold to move), **trigger** = gripper, **thumbstick click** = go to rest pose.

## 3. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/dev/ttyACM0` missing | Power Box not attached | `usbipd attach --wsl --busid <ARM_BUSID>` |
| `Permission denied: /dev/ttyACM0` | udev not running / not in `dialout` | Section 1; quick fix: `sudo chmod 666 /dev/ttyACM0` |
| `adb devices` is empty, but `cat /sys/bus/usb/devices/*/product` lists "Quest 3S" | USB node is root-only (udev not running) | Section 1; quick fix: `sudo chmod 666 /dev/bus/usb/*/*`, then `adb kill-server` |
| Quest missing from `/sys/bus/usb/devices` | attach dropped after re-enumeration | `usbipd attach --wsl --busid <QUEST_BUSID> --auto-attach` |
| `adb devices` says `unauthorized` | debugging prompt not accepted | In the headset, accept **Allow USB debugging** and tick **Always allow**. No prompt? Settings → System → Developer → Revoke USB debugging authorizations, then replug |
| `adb reverse --list` is empty | reverse is lost on every reconnect | `adb reverse tcp:8443 tcp:8443` |
| Everything runs, arm doesn't move | Quest isn't in the VR session, so no `xr_frame`s reach the relay | **Start Teleop**, accept the VR prompt, hold the **right** grip |
| Arm doesn't move after a while | headset slept, so the Quest dropped off USB | re-attach (if not `--auto-attach`), `adb reverse` again, re-enter VR |

Don't run adb on Windows and in WSL at the same time. They fight over the headset.
