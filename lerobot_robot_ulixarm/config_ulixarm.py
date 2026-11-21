from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig


@RobotConfig.register_subclass("ulixarm_follower")
@dataclass
class UlixArmFollowerConfig(RobotConfig):
    # USB port of the Power Box, e.g. /dev/ttyACM0 (on WSL2 attach it first with usbipd).
    port: str = "/dev/ttyACM0"
    gripper: bool = True
    # True when the RealSense D405 is mounted on the wrist: ulixpy then loads the matching URDF for gravity comp.
    camera_mounted: bool = False
    # Joint gains (Nm/rad, Nm*s/rad), J1..J6. Tuned on the real arm; kd = kp/10.
    # Itaca's docs suggest kp=20, kd=1 for a first bring-up, but that is too soft for teleop (lag, sag).
    kp: list[float] = field(default_factory=lambda: [200.0, 300.0, 200.0, 70.0, 50.0, 30.0])
    kd: list[float] = field(default_factory=lambda: [2.5, 3.5, 2.5, 0.7, 0.5, 0.5])
    gravity_compensation: bool = True
    # Max joint move per action, rad. ulixpy itself rejects jumps > 0.2 rad, so keep this below that.
    max_relative_target: float = 0.1
    # Gripper close strength 0..1, used when gripper.pos (closure) is ~1.
    grip_force: float = 0.5
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if len(self.kp) != 6 or len(self.kd) != 6:
            raise ValueError("kp and kd must have 6 values (J1..J6)")
        if not 0 < self.max_relative_target <= 0.2:
            raise ValueError("max_relative_target must be in (0, 0.2] rad; ulixpy rejects larger jumps")
        if self.camera_mounted and not self.gripper:
            raise ValueError("camera_mounted requires gripper=True (ulixpy constraint)")


@RobotConfig.register_subclass("ulixarm_duo_follower")
@dataclass
class UlixArmDuoFollowerConfig(UlixArmFollowerConfig):
    """Two Ulix Arms (bimanual). Every UlixArmFollowerConfig knob applies to both arms; `port` is unused."""

    left_arm_port: str = "/dev/ttyACM0"
    right_arm_port: str = "/dev/ttyACM1"

    def __post_init__(self):
        super().__post_init__()
        if self.left_arm_port == self.right_arm_port:
            raise ValueError("left_arm_port and right_arm_port must differ")
