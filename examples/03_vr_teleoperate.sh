#!/usr/bin/env bash
# Drive the Ulix Arm with a Meta Quest through LeRobot (no recording).
#
# Before running this, in two other terminals (both after `source /home/ostif/ulixarm_vr/env.sh`):
#   terminal 1:  vr-teleop-relay
#   terminal 2:  adb reverse tcp:8443 tcp:8443      # Quest over USB; re-run after replugging
# Quest browser -> http://localhost:8443/ -> "Calibrate wrist" (once) -> "Start Teleop".
#
# Nothing moves until you squeeze grip (the teleop is seeded from the measured joints).
# Grip = clutch, trigger = gripper, thumbstick click = go to the VR kit's rest pose.
# Ctrl-C stops; the arm then holds its pose.
set -euo pipefail
source /home/ostif/ulixarm_vr/env.sh

python -m lerobot_robot_ulixarm.vr teleoperate \
  --robot.type=ulixarm_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=ulix \
  --teleop.type=single_arm_quest_teleop \
  --teleop.id=quest \
  --teleop.arm=right \
  --teleop.ws_url=ws://127.0.0.1:8443/ws \
  --fps=60
