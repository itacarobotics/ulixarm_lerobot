# Teleoperation quickstart: UlixArm and UlixArmDuo

How to power up, connect, and teleoperate one Ulix Arm (`ulixarm_follower`) or two (`ulixarm_duo_follower`, "UlixArmDuo")
with a Meta Quest. One-time install and WSL/udev setup are in [README.md](README.md) and [WSL_SETUP.md](WSL_SETUP.md).

| | Single arm | UlixArmDuo (bimanual) |
|---|---|---|
| Power Boxes / USB ports | 1 (`/dev/ttyACM0`) | 2 (`/dev/ttyACM0`, `/dev/ttyACM1`) |
| LeRobot robot type | `ulixarm_follower` | `ulixarm_duo_follower` |
| LeRobot teleop type | `single_arm_quest_teleop` | `bi_quest_teleop` |
| Controllers used | one (`--teleop.arm=right` by default) | left controller → left arm, right → right arm |
| Action / observation keys | `joint_1.pos` … `gripper.pos` | `left_joint_1.pos` … `right_gripper.pos` |

## Safety first

- **Put every arm in its resting pose before starting.** Connecting enables the motors and holds the current pose.
- The arms have **no brakes and no collision detection**. Stay about 0.9 m clear of each shoulder. With two arms, also
  keep their reach zones apart: nothing stops one arm hitting the other.
- Stopping a script (Ctrl-C) leaves the arms **holding** their last pose. The motors stay on. Support the arm by hand before
  you cut power.

## 1. Start the hardware (every session)

1. Power on the Power Box(es) and plug each into USB. Plug in the Quest (USB-C).
2. **Windows (PowerShell)**: attach each device to WSL. Attaching is lost on every replug, sleep and reboot.

   ```powershell
   usbipd list                                            # Power Box = 2e88:4603, Quest = 2833:xxxx
   usbipd attach --wsl --busid <ARM_BUSID>                # duo: run this once for EACH Power Box
   usbipd attach --wsl --busid <QUEST_BUSID> --auto-attach
   ```

3. **WSL**: every terminal below starts with `source /home/ostif/ulixarm_vr/env.sh`. Then check the devices:

   ```bash
   cd /home/ostif/ulixarm_lerobot
   python examples/00_check_env.py      # checks the env and every /dev/ttyACM* (duo: expect two)
   adb devices                          # the Quest must say "device"
   ```

   **Duo: which port is which arm?** Ports are numbered in attach order, so check before the first run:
   `ls -l /dev/serial/by-id/`. Or run `examples/01_read_state.py` on one port and see which arm's joints change when you
   move it by hand. Set `LEFT_PORT` / `RIGHT_PORT` to match.

## 2. Start the VR relay and the Quest page

```bash
# terminal 1: relay that serves the Quest web page and streams controller poses
source /home/ostif/ulixarm_vr/env.sh
vr-teleop-relay

# terminal 2: forward the Quest's localhost:8443 to WSL over USB (re-run after every Quest replug or sleep)
source /home/ostif/ulixarm_vr/env.sh
adb reverse tcp:8443 tcp:8443
```

In the Quest browser:

1. Open `http://localhost:8443/`.
2. Tap **Calibrate wrist**. You only need to do this once per operator.
3. Tap **Start Teleop** and accept the VR prompt.
4. **Stay in VR.** Controller data only streams inside the immersive session. Taking the headset off or pressing the Meta
   button pauses it.

## 3a. Teleoperate a single arm

Terminal 3, with the arm in its resting pose:

```bash
source /home/ostif/ulixarm_vr/env.sh
cd /home/ostif/ulixarm_lerobot
bash examples/03_vr_teleoperate.sh
```

This runs the following command. Edit `--robot.port` or `--teleop.arm=left|right` to choose the port and controller:

```bash
python -m lerobot_robot_ulixarm.vr teleoperate \
  --robot.type=ulixarm_follower --robot.port=/dev/ttyACM0 --robot.id=ulix \
  --teleop.type=single_arm_quest_teleop --teleop.id=quest --teleop.arm=right \
  --teleop.ws_url=ws://127.0.0.1:8443/ws --fps=60
```

## 3b. Teleoperate UlixArmDuo (two arms)

Terminal 3, with both arms in their resting pose:

```bash
source /home/ostif/ulixarm_vr/env.sh
cd /home/ostif/ulixarm_lerobot
LEFT_PORT=/dev/ttyACM0 RIGHT_PORT=/dev/ttyACM1 bash examples/06_vr_duo_teleoperate.sh
```

This runs:

```bash
python -m lerobot_robot_ulixarm.vr teleoperate \
  --robot.type=ulixarm_duo_follower \
  --robot.left_arm_port=/dev/ttyACM0 --robot.right_arm_port=/dev/ttyACM1 --robot.id=ulix_duo \
  --teleop.type=bi_quest_teleop --teleop.id=quest \
  --teleop.ws_url=ws://127.0.0.1:8443/ws --fps=60
```

Mount both arms **facing the same direction**: both share one Quest-to-arm rotation. Every `--robot.*` setting, such as
`kp`, `kd`, `max_relative_target` and `grip_force`, applies to both arms.

## 4. Controller mapping

Nothing moves at startup. The teleop is seeded from each arm's measured joints, so an arm only moves while you hold its grip.

| Button | Action |
|---|---|
| **Grip** (hold) | Clutch: while held, the arm follows the hand. Release, move the hand, and squeeze again to re-center. |
| **Trigger** | Gripper: 0 = open, fully pressed = close with `grip_force`. |
| **A / X** (hold) | Precision mode: scales the motion down for fine work. |
| **Thumbstick click** | Ramps that arm to the VR kit's rest pose over about 2 s. |

In single-arm mode only the chosen controller (`--teleop.arm`) drives the arm. In duo mode each controller drives the arm on
its side.

## 5. Stop

Press **Ctrl-C** in terminal 3. Each arm calls `hold()` and stays where it is, with the motors on. Before switching the
Power Box off, move the arms back to rest (thumbstick click, or by hand while supporting them).

## Record demos instead of just teleoperating

Replace `teleoperate` with `record` and add the dataset flags. Single arm: see `examples/04_vr_record.sh`. Duo: use the
command from 3b plus the following:

```bash
  --robot.cameras="{left_wrist: {type: intelrealsense, serial_number_or_name: '<SERIAL_L>', width: 640, height: 480, fps: 30}, right_wrist: {type: intelrealsense, serial_number_or_name: '<SERIAL_R>', width: 640, height: 480, fps: 30}}" \
  --robot.camera_mounted=true \
  --dataset.repo_id=local/ulix_duo_task --dataset.single_task="..." \
  --dataset.num_episodes=20 --dataset.fps=30 --dataset.push_to_hub=false
```

Leave out the camera lines to record joints only.

## Without LeRobot: the VR kit's standalone loop

`ulixarm_vr/vr-teleop-kit/examples/teleop_ulixarm.py` drives the arms directly through ulixpy at 200 Hz. It uses the same
relay and Quest setup, and soft default gains (kp=20, kd=1):

```bash
cd /home/ostif/ulixarm_vr/vr-teleop-kit
python examples/teleop_ulixarm.py --port /dev/ttyACM0 --hand right                                # one arm
python examples/teleop_ulixarm.py --hand both --left-port /dev/ttyACM0 --right-port /dev/ttyACM1  # UlixArmDuo
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/dev/ttyACM0` or `/dev/ttyACM1` missing | `usbipd attach --wsl --busid <BUSID>` for that Power Box |
| `left_arm_port and right_arm_port must differ` | Pass two different ports |
| Wrong arm moves | The ports are swapped. Swap `LEFT_PORT` / `RIGHT_PORT` |
| Script runs but nothing moves | Not in the VR session, or not holding grip. Tap **Start Teleop**, accept, then squeeze grip |
| Stops responding after a while | The headset slept. Re-attach the Quest, run `adb reverse tcp:8443 tcp:8443` again, re-enter VR |
| `Joint goal clamped` warnings | Normal during fast hand motion: each action moves at most `max_relative_target` (0.1 rad) |

More WSL/adb cases: [WSL_SETUP.md § Troubleshooting](WSL_SETUP.md#3-troubleshooting).
