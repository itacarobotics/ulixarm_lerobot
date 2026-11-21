#!/usr/bin/env bash
# Record a LeRobot dataset of VR-teleoperated demos, with the wrist RealSense D405.
# Same relay + Quest setup as 03_vr_teleoperate.sh.
#
# Needs: pip install pyrealsense2   (find the serial with: lerobot-find-cameras realsense)
# Keys while recording: -> next episode, <- redo episode, Esc stop.
# Remove the --robot.cameras / camera_mounted lines to record joints only.
set -euo pipefail
source /home/ostif/ulixarm_vr/env.sh

HF_USER=${HF_USER:-local}        # your Hugging Face user if you push to the Hub
CAM_SERIAL=${CAM_SERIAL:?set CAM_SERIAL to the D405 serial number}

python -m lerobot_robot_ulixarm.vr record \
  --robot.type=ulixarm_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=ulix \
  --robot.camera_mounted=true \
  --robot.cameras="{wrist: {type: intelrealsense, serial_number_or_name: '$CAM_SERIAL', width: 640, height: 480, fps: 30}}" \
  --teleop.type=single_arm_quest_teleop \
  --teleop.id=quest \
  --teleop.arm=right \
  --dataset.repo_id="$HF_USER/ulix_pick_cube" \
  --dataset.single_task="Pick up the cube and place it in the box" \
  --dataset.num_episodes=20 \
  --dataset.episode_time_s=40 \
  --dataset.reset_time_s=15 \
  --dataset.fps=30 \
  --dataset.push_to_hub=false \
  --display_data=true
