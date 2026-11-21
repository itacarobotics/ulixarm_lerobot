import logging
from functools import cached_property

import numpy as np
from lerobot.cameras import make_cameras_from_configs
from lerobot.robots.robot import Robot
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected
from ulixpy import UlixArm

from .config_ulixarm import UlixArmFollowerConfig

logger = logging.getLogger(__name__)

JOINTS = [f"joint_{i}" for i in range(1, 7)]
_GRIP = 0.95  # closure above which we grip with force instead of position


class UlixArmFollower(Robot):
    """Ulix Arm driven through ulixpy. Joints in radians, gripper 0 (open)..1 (closed) like vr-teleop-kit."""

    config_class = UlixArmFollowerConfig
    name = "ulixarm_follower"
    supports_position_hold = True

    def __init__(self, config: UlixArmFollowerConfig):
        super().__init__(config)
        self.config = config
        self.arm: UlixArm | None = None
        self.cameras = make_cameras_from_configs(config.cameras)
        self._kp = np.asarray(config.kp, dtype=float)
        self._kd = np.asarray(config.kd, dtype=float)
        self._zero = np.zeros(6)
        self._gripper_cmd: float | None = None

    @property
    def _motors_ft(self) -> dict[str, type]:
        names = JOINTS + (["gripper"] if self.config.gripper else [])
        return {f"{n}.pos": float for n in names}

    @cached_property
    def observation_features(self) -> dict:
        cams = {k: (c.height, c.width, 3) for k, c in self.config.cameras.items()}
        return {**self._motors_ft, **cams}

    @cached_property
    def action_features(self) -> dict:
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        return self.arm is not None and all(c.is_connected for c in self.cameras.values())

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        arm = UlixArm(gripper=self.config.gripper, camera=self.config.camera_mounted)
        arm.connect(self.config.port)
        self.arm = arm
        self.configure()
        for cam in self.cameras.values():
            cam.connect()
        logger.info(f"{self} connected.")

    @property
    def is_calibrated(self) -> bool:
        return True  # ulixpy exposes no user calibration; joint zeros come from the factory

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        # Itaca: enable only in the resting pose; there is no holding torque until hold()/control().
        self.arm.enable()
        self.arm.refresh()
        self.arm.hold()
        if self.config.gripper:
            self._gripper_cmd = 0.0
            self.arm.open_ratio(1.0)

    def hold(self) -> None:
        self.arm.hold()

    @check_if_not_connected
    def get_observation(self) -> dict:
        self.arm.refresh()
        obs = dict(zip([f"{j}.pos" for j in JOINTS], map(float, self.arm.get_q()), strict=True))
        if self.config.gripper:
            # shortcut: ulixpy has no gripper position readback, so we report the last command; swap in a real reading if ulixpy adds one.
            obs["gripper.pos"] = self._gripper_cmd
        for key, cam in self.cameras.items():
            obs[key] = cam.read_latest()
        return obs

    @check_if_not_connected
    def send_action(self, action: dict) -> dict:
        q_goal = np.array([action[f"{j}.pos"] for j in JOINTS], dtype=float)
        self.arm.refresh()  # get_q() raises if feedback is >500 ms old, e.g. after a pause between actions
        q = self.arm.get_q()
        step = self.config.max_relative_target
        q_safe = np.clip(q_goal, q - step, q + step)
        if not np.allclose(q_safe, q_goal):
            logger.warning("Joint goal clamped to max_relative_target=%.3f rad", step)
        self.arm.control(q_safe, self._zero, self._zero, self._kp, self._kd, self.config.gravity_compensation)
        sent = {f"{j}.pos": float(v) for j, v in zip(JOINTS, q_safe, strict=True)}

        if self.config.gripper:
            r = float(np.clip(action["gripper.pos"], 0.0, 1.0))
            # Gripper calls are non-blocking; only re-send when the command really changes.
            if self._gripper_cmd is None or abs(r - self._gripper_cmd) > 0.01:
                if r > _GRIP:
                    self.arm.close(self.config.grip_force)
                else:
                    self.arm.open_ratio(1.0 - r)
                self._gripper_cmd = r
            sent["gripper.pos"] = r
        return sent

    @check_if_not_connected
    def disconnect(self) -> None:
        # Motors keep the last command after disconnect, so leave them holding (disable() would drop the arm).
        try:
            self.arm.hold()
        finally:
            self.arm.disconnect()
            self.arm = None
            for cam in self.cameras.values():
                cam.disconnect()
        logger.info(f"{self} disconnected.")
