#!/usr/bin/env bash
# After 04_vr_record.sh: replay a demo, train a policy, and run it on the arm.
# Run one step at a time (comment out the rest); training needs a GPU to be practical.
set -euo pipefail
source /home/ostif/ulixarm_vr/env.sh

HF_USER=${HF_USER:-local}
CAM_SERIAL=${CAM_SERIAL:?set CAM_SERIAL to the D405 serial number}
ROBOT=(--robot.type=ulixarm_follower --robot.port=/dev/ttyACM0 --robot.id=ulix --robot.camera_mounted=true)

# 1. Replay episode 0 on the arm. Start from the resting pose: the arm drives to the
#    episode's first pose at max_relative_target per frame.
lerobot-replay "${ROBOT[@]}" \
  --dataset.repo_id="$HF_USER/ulix_pick_cube" --dataset.episode=0

# 2. Train an ACT policy on the recorded demos.
lerobot-train \
  --dataset.repo_id="$HF_USER/ulix_pick_cube" \
  --policy.type=act \
  --policy.device=cuda \
  --policy.push_to_hub=false \
  --output_dir=outputs/train/act_ulix_pick_cube \
  --job_name=act_ulix_pick_cube

# 3. Run the policy and record evaluation episodes. The camera key must match training ("wrist").
lerobot-record "${ROBOT[@]}" \
  --robot.cameras="{wrist: {type: intelrealsense, serial_number_or_name: '$CAM_SERIAL', width: 640, height: 480, fps: 30}}" \
  --policy.path=outputs/train/act_ulix_pick_cube/checkpoints/last/pretrained_model \
  --dataset.repo_id="$HF_USER/eval_ulix_pick_cube" \
  --dataset.single_task="Pick up the cube and place it in the box" \
  --dataset.num_episodes=5 \
  --dataset.push_to_hub=false
