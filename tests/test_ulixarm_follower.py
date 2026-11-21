"""Runs without hardware: a fake ulixpy stands in for the real arm."""

import sys
import types

import numpy as np
import pytest


class FakeArm:
    def __init__(self, gripper=True, camera=False, urdf_path=""):
        self.q = np.zeros(6)
        self.calls = []

    def __getattr__(self, name):  # record any other ulixpy call (enable, hold, open_ratio, ...)
        return lambda *a: self.calls.append((name, a))

    def get_q(self):
        return self.q.copy()

    def control(self, q, dq, tau, kp, kd, gravity):
        assert np.all(np.abs(q - self.q) <= 0.2), "ulixpy would reject a >0.2 rad jump"
        self.calls.append(("control", (q, gravity)))
        self.q = q


sys.modules.setdefault("ulixpy", types.SimpleNamespace(UlixArm=FakeArm, UlixArmError=RuntimeError))

from lerobot_robot_ulixarm import UlixArmFollower, UlixArmFollowerConfig  # noqa: E402


def test_follower_roundtrip():
    robot = UlixArmFollower(UlixArmFollowerConfig(id="test"))
    robot.connect()
    names = [c[0] for c in robot.arm.calls]
    assert names[:4] == ["connect", "enable", "refresh", "hold"]

    obs = robot.get_observation()
    assert set(obs) == set(robot.observation_features)

    action = {f"joint_{i}.pos": 1.0 for i in range(1, 7)} | {"gripper.pos": 1.0}
    sent = robot.send_action(action)
    assert sent["joint_1.pos"] == pytest.approx(0.1)  # clamped to max_relative_target
    assert ("close", (0.5,)) in robot.arm.calls

    arm = robot.arm
    robot.disconnect()
    assert [c[0] for c in arm.calls[-2:]] == ["hold", "disconnect"]
    assert not robot.is_connected


def test_config_rejects_unsafe_step():
    with pytest.raises(ValueError):
        UlixArmFollowerConfig(max_relative_target=0.5)


def test_duo_roundtrip():
    from lerobot_robot_ulixarm import UlixArmDuoFollower, UlixArmDuoFollowerConfig

    robot = UlixArmDuoFollower(UlixArmDuoFollowerConfig(id="duo"))
    assert robot.arms["left"].config.port == "/dev/ttyACM0" and robot.arms["right"].config.port == "/dev/ttyACM1"
    assert robot.arms["right"].config.id == "duo_right"
    robot.connect()

    obs = robot.get_observation()
    assert set(obs) == set(robot.observation_features)
    assert "left_joint_1.pos" in obs and "right_gripper.pos" in obs

    action = {f"{s}_joint_{i}.pos": 1.0 for s in ("left", "right") for i in range(1, 7)}
    action |= {"left_gripper.pos": 0.0, "right_gripper.pos": 1.0}
    sent = robot.send_action(action)
    assert set(sent) == set(robot.action_features)
    assert sent["right_joint_1.pos"] == pytest.approx(0.1)
    assert ("close", (0.5,)) in robot.arms["right"].arm.calls
    assert ("close", (0.5,)) not in robot.arms["left"].arm.calls

    robot.disconnect()
    assert not robot.is_connected


def test_duo_config_rejects_same_port():
    from lerobot_robot_ulixarm import UlixArmDuoFollowerConfig

    with pytest.raises(ValueError):
        UlixArmDuoFollowerConfig(left_arm_port="/dev/ttyACM0", right_arm_port="/dev/ttyACM0")
