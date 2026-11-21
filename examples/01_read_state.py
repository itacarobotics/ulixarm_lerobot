"""Connect and print the arm state for 5 s. The arm holds its pose, it does not move.

    source /home/ostif/ulixarm_vr/env.sh
    python examples/01_read_state.py --port /dev/ttyACM0

Start with the arm in its resting pose: connect() enables the motors.
"""

import argparse
import time

from lerobot_robot_ulixarm import UlixArmFollower, UlixArmFollowerConfig

ap = argparse.ArgumentParser()
ap.add_argument("--port", default="/dev/ttyACM0")
args = ap.parse_args()

robot = UlixArmFollower(UlixArmFollowerConfig(port=args.port, id="ulix"))
robot.connect()
try:
    print("observation features:", robot.observation_features)
    for _ in range(10):
        obs = robot.get_observation()
        print("  ".join(f"{k.removesuffix('.pos')}={v:+.3f}" for k, v in obs.items()))
        time.sleep(0.5)
finally:
    robot.disconnect()  # holds the pose, never drops the arm
