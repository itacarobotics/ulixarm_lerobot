#!/usr/bin/env bash
# Drive two Ulix Arms (UlixArmDuo) with both Meta Quest controllers: left controller -> left arm, right -> right.
# Same relay + Quest setup as 03_vr_teleoperate.sh. Each Power Box shows up as its own port; check which is which
# with `ls -l /dev/serial/by-id/` (on WSL2, usbipd-attach both).
#
# Both arms must be mounted facing the same way: the teleop uses one Quest->base rotation (r_calib) for both.
# To record instead, swap `teleoperate` for `record` and add the --dataset.* flags from 04_vr_record.sh.
set -euo pipefail
source /home/ostif/ulixarm_vr/env.sh

python -m lerobot_robot_ulixarm.vr teleoperate \
  --robot.type=ulixarm_duo_follower \
  --robot.left_arm_port=${LEFT_PORT:-/dev/ttyACM0} \
  --robot.right_arm_port=${RIGHT_PORT:-/dev/ttyACM1} \
  --robot.id=ulix_duo \
  --teleop.type=bi_quest_teleop \
  --teleop.id=quest \
  --teleop.ws_url=ws://127.0.0.1:8443/ws \
  --fps=60
