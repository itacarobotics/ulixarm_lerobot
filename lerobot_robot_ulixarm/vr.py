"""Run lerobot-teleoperate / lerobot-record with the Quest VR teleop (vr-teleop-kit) on a Ulix Arm.

    python -m lerobot_robot_ulixarm.vr teleoperate --robot.type=ulixarm_follower ... --teleop.type=single_arm_quest_teleop ...
    python -m lerobot_robot_ulixarm.vr record      --robot.type=ulixarm_follower ... --teleop.type=single_arm_quest_teleop ...
    python -m lerobot_robot_ulixarm.vr teleoperate --robot.type=ulixarm_duo_follower ... --teleop.type=bi_quest_teleop ...

Why a wrapper and not the plain CLIs:
  1. vr-teleop-kit isn't a `lerobot_teleoperator_*` package, so LeRobot never imports it on its own.
  2. The VR teleop starts at its own rest pose (not the Ulix resting pose). Unseeded, the first actions would
     drive the arm there. We seed it from the measured joints, so nothing moves until you squeeze grip.
"""

import os
import sys

os.environ.setdefault("VR_TELEOP_ROBOT", "ulixarm")  # must be set before vr_teleop_kit is imported

from vr_teleop_kit.lerobot import BiQuestTeleoperator, SingleArmQuestTeleoperator  # noqa: E402  (import also registers the teleop types)

from .ulixarm_duo_follower import UlixArmDuoFollower  # noqa: E402
from .ulixarm_follower import UlixArmFollower  # noqa: E402

_robots: list = []


def _track(connect):
    def robot_connect(self, *args, **kwargs):
        connect(self, *args, **kwargs)
        _robots.append(self)  # a duo appends after its two arms, so _robots[-1] is the top-level robot

    return robot_connect


def _seed_first(get_action):
    def teleop_get_action(self):
        if not getattr(self, "_ulix_seeded", False) and _robots:
            # Both LeRobot scripts connect robot + teleop before the first get_action().
            obs = _robots[-1].get_observation()
            self.seed_qpos_from_obs({k: v for k, v in obs.items() if k.endswith(".pos")})
            self._ulix_seeded = True
            # The single-arm teleop wraps a BiQuestTeleoperator (_inner) that it just seeded; don't re-seed it.
            getattr(self, "_inner", self)._ulix_seeded = True
        return get_action(self)

    return teleop_get_action


def _install_seeding() -> None:
    for robot_cls in (UlixArmFollower, UlixArmDuoFollower):
        robot_cls.connect = _track(robot_cls.connect)
    for teleop_cls in (SingleArmQuestTeleoperator, BiQuestTeleoperator):
        teleop_cls.get_action = _seed_first(teleop_cls.get_action)


def main() -> None:
    cmds = {"teleoperate", "record"}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m lerobot_robot_ulixarm.vr {{{'|'.join(sorted(cmds))}}} [lerobot args...]")
    cmd = sys.argv.pop(1)
    _install_seeding()
    if cmd == "teleoperate":
        from lerobot.scripts.lerobot_teleoperate import main as run
    else:
        from lerobot.scripts.lerobot_record import main as run
    run()


if __name__ == "__main__":
    main()
