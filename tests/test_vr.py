"""The VR wrapper must seed the teleop from the measured arm before the first action (no startup jump)."""

import types

import pytest

pytest.importorskip("vr_teleop_kit")
import test_ulixarm_follower  # noqa: E402,F401  (installs the fake ulixpy)

from lerobot_robot_ulixarm import UlixArmFollower, UlixArmFollowerConfig, vr  # noqa: E402


def test_teleop_seeded_from_robot_once():
    vr._install_seeding()
    robot = UlixArmFollower(UlixArmFollowerConfig(id="test"))
    robot.connect()
    robot.arm.q[:] = 0.3

    seeds = []
    teleop = types.SimpleNamespace(
        _prefix="right_",
        _inner=types.SimpleNamespace(get_action=lambda: {"right_joint_1.pos": 0.3, "left_joint_1.pos": 9.0}),
        seed_qpos_from_obs=seeds.append,
    )
    action = vr.SingleArmQuestTeleoperator.get_action(teleop)
    vr.SingleArmQuestTeleoperator.get_action(teleop)

    assert action == {"joint_1.pos": 0.3}
    assert len(seeds) == 1 and seeds[0]["joint_1.pos"] == pytest.approx(0.3)
    robot.disconnect()


def test_bi_teleop_seeded_from_duo():
    from lerobot_robot_ulixarm import UlixArmDuoFollower, UlixArmDuoFollowerConfig

    vr._install_seeding()
    robot = UlixArmDuoFollower(UlixArmDuoFollowerConfig(id="duo"))
    robot.connect()
    robot.arms["left"].arm.q[:] = 0.2
    robot.arms["right"].arm.q[:] = -0.4

    from vr_teleop_kit.lerobot import BiQuestTeleoperatorConfig

    teleop = vr.BiQuestTeleoperator(BiQuestTeleoperatorConfig(id="quest", publish_ik_state=False))
    action = teleop.get_action()  # no WS connected -> returns the (seeded) internal pose

    assert action["left_joint_1.pos"] == pytest.approx(0.2)
    assert action["right_joint_6.pos"] == pytest.approx(-0.4)
    robot.disconnect()
