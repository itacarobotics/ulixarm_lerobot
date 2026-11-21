"""Check the Python env for Ulix Arm + LeRobot + VR teleop. No hardware needed; nothing moves.

    source /home/ostif/ulixarm_vr/env.sh
    python examples/00_check_env.py
"""

import glob
import grp
import importlib
import importlib.util
import os
import subprocess
import sys

failed = False


def check(name, ok, hint=""):
    global failed
    failed |= not ok
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + ("" if ok else f"  -> {hint}"))


print("python", sys.version.split()[0], sys.executable)
check("Python >= 3.12 (latest LeRobot)", sys.version_info >= (3, 12), "recreate ulixenv with Python 3.12")

for mod in ["ulixpy", "torch", "lerobot", "lerobot_robot_ulixarm", "vr_teleop_kit.lerobot", "lerobot_robot_ulixarm.vr"]:
    try:
        importlib.import_module(mod)
        check(f"import {mod}", True)
    except Exception as e:
        check(f"import {mod}", False, f"{type(e).__name__}: {e}")

for mod, extra, use in [("datasets", "dataset", "lerobot-record"), ("pyrealsense2", "intelrealsense", "RealSense camera")]:
    check(f"{mod} (for {use})", importlib.util.find_spec(mod) is not None, f"pip install 'lerobot[{extra}]'")

# ulixpy's native libs must all come from the pin wheel, not /opt/openrobots or ROS
import ulixpy  # noqa: E402

so = glob.glob(os.path.join(os.path.dirname(ulixpy.__file__), "_core*.so"))[0]
foreign = [ln.strip() for ln in subprocess.run(["ldd", so], capture_output=True, text=True).stdout.splitlines()
           if "/opt/" in ln]
check("ulixpy links only pin-wheel libraries", not foreign, "source env.sh (clears LD_LIBRARY_PATH): " + "; ".join(foreign[:3]))

try:
    ulixpy.UlixArm()
    check("ulixpy.UlixArm() loads its URDF", True)
except Exception as e:
    check("ulixpy.UlixArm() loads its URDF", False, str(e))

from lerobot.robots.config import RobotConfig  # noqa: E402
from lerobot.teleoperators.config import TeleoperatorConfig  # noqa: E402

check("robot type ulixarm_follower", "ulixarm_follower" in RobotConfig.get_known_choices(), "pip install -e /home/ostif/ulixarm_lerobot")
check("teleop type single_arm_quest_teleop", "single_arm_quest_teleop" in TeleoperatorConfig.get_known_choices(),
      "pip install -e '/home/ostif/ulixarm_vr/vr-teleop-kit[relay,lerobot]'")
check("VR_TELEOP_ROBOT=ulixarm", os.environ.get("VR_TELEOP_ROBOT") == "ulixarm", "source /home/ostif/ulixarm_vr/env.sh")
check("ULIXARM_URDF exists", os.path.isfile(os.environ.get("ULIXARM_URDF", "")), "source /home/ostif/ulixarm_vr/env.sh")

ports = glob.glob("/dev/ttyACM*")
check(f"USB port present {ports}", bool(ports), "plug in the Power Box; on WSL2: usbipd attach --wsl --busid <BUSID>")
check("user in dialout group", grp.getgrnam("dialout").gr_gid in os.getgroups(),
      "sudo usermod -aG dialout $USER, then log out/in (WSL2: wsl --shutdown)")

sys.stdout.flush()
os._exit(1 if failed else 0)  # skip interpreter teardown so a native-lib clash can't mask the report
