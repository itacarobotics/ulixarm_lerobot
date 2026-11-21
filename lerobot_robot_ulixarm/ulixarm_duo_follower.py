import dataclasses
import logging
from functools import cached_property

from lerobot.cameras import make_cameras_from_configs
from lerobot.robots.robot import Robot
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from .config_ulixarm import UlixArmDuoFollowerConfig, UlixArmFollowerConfig
from .ulixarm_follower import UlixArmFollower

logger = logging.getLogger(__name__)

SIDES = ("left", "right")


class UlixArmDuoFollower(Robot):
    """Two UlixArmFollowers; keys prefixed `left_` / `right_` like vr-teleop-kit's bi_quest_teleop."""

    config_class = UlixArmDuoFollowerConfig
    name = "ulixarm_duo_follower"
    supports_position_hold = True

    def __init__(self, config: UlixArmDuoFollowerConfig):
        super().__init__(config)
        self.config = config
        shared = {f.name: getattr(config, f.name) for f in dataclasses.fields(UlixArmFollowerConfig)}
        self.arms = {
            side: UlixArmFollower(UlixArmFollowerConfig(**{
                **shared,
                "id": f"{config.id}_{side}" if config.id else None,
                "port": getattr(config, f"{side}_arm_port"),
                "cameras": {},  # cameras belong to the duo, not to one arm
            }))
            for side in SIDES
        }
        self.cameras = make_cameras_from_configs(config.cameras)

    def _prefixed(self, feats: dict) -> dict:
        return {f"{side}_{k}": v for side in SIDES for k, v in feats(self.arms[side]).items()}

    @cached_property
    def observation_features(self) -> dict:
        cams = {k: (c.height, c.width, 3) for k, c in self.config.cameras.items()}
        return {**self._prefixed(lambda a: a.observation_features), **cams}

    @cached_property
    def action_features(self) -> dict:
        return self._prefixed(lambda a: a.action_features)

    @property
    def is_connected(self) -> bool:
        return all(a.is_connected for a in self.arms.values()) and all(c.is_connected for c in self.cameras.values())

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        self.arms["left"].connect(calibrate)
        try:
            self.arms["right"].connect(calibrate)
        except Exception:
            self.arms["left"].disconnect()  # leave the first arm holding, not half-connected
            raise
        for cam in self.cameras.values():
            cam.connect()
        logger.info(f"{self} connected.")

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        for arm in self.arms.values():
            arm.configure()

    def hold(self) -> None:
        for arm in self.arms.values():
            arm.hold()

    @check_if_not_connected
    def get_observation(self) -> dict:
        obs = {f"{side}_{k}": v for side in SIDES for k, v in self.arms[side].get_observation().items()}
        for key, cam in self.cameras.items():
            obs[key] = cam.read_latest()
        return obs

    @check_if_not_connected
    def send_action(self, action: dict) -> dict:
        sent = {}
        for side in SIDES:
            p = f"{side}_"
            arm_action = {k.removeprefix(p): v for k, v in action.items() if k.startswith(p)}
            sent |= {p + k: v for k, v in self.arms[side].send_action(arm_action).items()}
        return sent

    @check_if_not_connected
    def disconnect(self) -> None:
        try:
            for arm in self.arms.values():
                if arm.is_connected:
                    arm.disconnect()
        finally:
            for cam in self.cameras.values():
                cam.disconnect()
        logger.info(f"{self} disconnected.")
