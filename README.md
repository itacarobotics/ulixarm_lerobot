# lerobot_robot_ulixarm

LeRobot plugin for the Itaca Robotics Ulix Arm, built on [ulixpy](https://itacarobotics.com/docs/api/ulixpy).
LeRobot finds it automatically through the `lerobot_robot_` package prefix. Robot types: `ulixarm_follower` (one arm) and `ulixarm_duo_follower` (two arms, see [Bimanual](#bimanual-ulixarmduo)).

- Actions and observations: `joint_1.pos` … `joint_6.pos` in **radians**, plus `gripper.pos` from 0 (open) to
  1 (closed). Above 0.95 the gripper closes with force `grip_force`.
- Each action moves every joint at most `max_relative_target` rad (default 0.1). ulixpy itself rejects moves over 0.2 rad.
- Control is ulixpy's impedance law with gravity compensation. Default gains are kp=[250, 350, 250, 120, 80, 40] and kd=kp/10; override with `--robot.kp` / `--robot.kd`.

## Install

Works with LeRobot 0.4.4 on Python 3.10 (the `ulixenv` from `/home/ostif/ulixarm_vr/env.sh`), and with newer LeRobot on 3.12:

```bash
sudo apt install -y build-essential cmake git pkg-config libeigen3-dev libserialport-dev
sudo usermod -aG dialout $USER          # then log out/in (WSL2: `wsl --shutdown`)
pip install -e .                        # pulls lerobot + ulixpy (ulixpy compiles from source)
```

On WSL2, attach the Power Box USB first, and again after every replug or reboot. From Windows: `usbipd attach --wsl --busid <BUSID>`.
Full WSL setup for the arm, Quest (adb) and D405, with troubleshooting: [WSL_SETUP.md](WSL_SETUP.md).

**Step-by-step startup and teleoperation, single arm and UlixArmDuo: [TELEOP.md](TELEOP.md).**

## Safety (from Itaca's docs)

- **Start with the arm in its resting pose.** `connect()` enables the motors and holds the current pose right away.
- The arm has no brakes. Stopping a script leaves the motors on the last command. `disconnect()` calls `hold()` and does not disable the motors.
- The arm has no collision detection. Stay about 0.9 m clear of the shoulder.

## Examples

| File | What it does |
|---|---|
| `examples/00_check_env.py` | Checks the Python env, libraries, USB port and permissions. No hardware needed. |
| `examples/01_read_state.py` | Connects and prints the joints. The arm doesn't move. |
| `examples/02_move_joint.py` | Moves one joint smoothly there and back, then closes and opens the gripper. |
| `examples/03_vr_teleoperate.sh` | Drives the arm with a Meta Quest through `../ulixarm_vr/vr-teleop-kit`. |
| `examples/04_vr_record.sh` | Records a dataset of VR demos with the wrist D405 camera. |
| `examples/05_replay_train_run.sh` | Replays a demo, trains ACT, then runs the policy. |
| `examples/06_vr_duo_teleoperate.sh` | Drives two arms (UlixArmDuo) with both Quest controllers. |

For VR, run `python -m lerobot_robot_ulixarm.vr {teleoperate|record} ...` instead of the plain `lerobot-*` commands. The wrapper:

- registers `single_arm_quest_teleop` with LeRobot;
- seeds the VR teleop from the measured joints, so the arm doesn't jump to the VR kit's rest pose at startup.

The gripper uses the VR kit's convention: `gripper.pos` 0 = open, 1 = closed.

## Bimanual (UlixArmDuo)

`UlixArmDuoFollower` (`--robot.type=ulixarm_duo_follower`) runs two `UlixArmFollower`s, one per Power Box:

- Keys are prefixed `left_` / `right_` (`left_joint_1.pos`, …, `right_gripper.pos`). These match the VR kit's
  `bi_quest_teleop`, so the two plug together with no mapping.
- Ports come from `--robot.left_arm_port` / `--robot.right_arm_port` (defaults `/dev/ttyACM0` / `/dev/ttyACM1`).
  Every other knob (`kp`, `kd`, `max_relative_target`, `grip_force`, `camera_mounted`, …) applies to both arms.
  `--robot.port` is ignored.
- Cameras belong to the duo: `--robot.cameras='{left_wrist: {...}, right_wrist: {...}}'`.

```bash
python -m lerobot_robot_ulixarm.vr teleoperate \
  --robot.type=ulixarm_duo_follower --robot.left_arm_port=/dev/ttyACM0 --robot.right_arm_port=/dev/ttyACM1 \
  --robot.id=ulix_duo --teleop.type=bi_quest_teleop --teleop.id=quest
```

The VR wrapper seeds `bi_quest_teleop` from both arms' measured joints, so neither arm moves until you squeeze its grip.

## Smoke test

```python
from lerobot_robot_ulixarm import UlixArmFollower, UlixArmFollowerConfig

robot = UlixArmFollower(UlixArmFollowerConfig(port="/dev/ttyACM0", id="ulix"))
robot.connect()
try:
    obs = robot.get_observation()
    print(obs)
    goal = {k: v for k, v in obs.items() if k.endswith(".pos")}
    goal["joint_6.pos"] += 0.05                 # small wrist nudge
    robot.send_action(goal)
finally:
    robot.disconnect()
```

## Use with LeRobot CLIs

```bash
# Run a trained policy / record evaluation episodes (wrist RealSense D405 as an RGB camera)
lerobot-record \
  --robot.type=ulixarm_follower --robot.port=/dev/ttyACM0 --robot.id=ulix \
  --robot.camera_mounted=true \
  --robot.cameras='{wrist: {type: intelrealsense, serial_number_or_name: "<SERIAL>", width: 640, height: 480, fps: 30}}' \
  --policy.path=<hf_user>/<policy> \
  --dataset.repo_id=<hf_user>/eval_ulix --dataset.single_task="..." --dataset.num_episodes=5

# Replay a recorded episode
lerobot-replay --robot.type=ulixarm_follower --robot.port=/dev/ttyACM0 --robot.id=ulix \
  --dataset.repo_id=<hf_user>/<dataset> --dataset.episode=0
```

Find the camera serial with `lerobot-find-cameras realsense`.

## Tests (no hardware)

```bash
pytest tests
```
