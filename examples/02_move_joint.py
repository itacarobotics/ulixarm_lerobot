"""Smoothly move one joint by a small angle and back, then open/close the gripper.

    source /home/ostif/ulixarm_vr/env.sh
    python examples/02_move_joint.py --joint 6 --delta 0.3

Same send_action() a policy or teleop uses: joints in rad, gripper 0 = open .. 1 = closed.
Keep ~0.9 m clear of the shoulder.
"""

import argparse
import time

import numpy as np

from lerobot_robot_ulixarm import UlixArmFollower, UlixArmFollowerConfig

ap = argparse.ArgumentParser()
ap.add_argument("--port", default="/dev/ttyACM0")
ap.add_argument("--joint", type=int, default=6, choices=range(1, 7))
ap.add_argument("--delta", type=float, default=0.3, help="rad")
ap.add_argument("--seconds", type=float, default=2.0, help="duration of each leg")
args = ap.parse_args()

HZ = 50
robot = UlixArmFollower(UlixArmFollowerConfig(port=args.port, id="ulix"))
robot.connect()
try:
    start = {k: v for k, v in robot.get_observation().items() if k.endswith(".pos")}
    key = f"joint_{args.joint}.pos"
    # 0 -> delta -> 0 with a cosine profile, so the speed starts and ends at zero
    for s in np.linspace(0, 2 * np.pi, int(2 * args.seconds * HZ)):
        robot.send_action({**start, key: start[key] + args.delta * (1 - np.cos(s)) / 2})
        time.sleep(1 / HZ)

    for closure in (1.0, 0.0):  # close, then open
        robot.send_action({**start, "gripper.pos": closure})
        time.sleep(1.5)  # gripper calls are non-blocking
finally:
    robot.disconnect()
