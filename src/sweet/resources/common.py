from dataclasses import dataclass
from ..core.linalg.vector import Vec3
from ..core.linalg.rotation import QuaternionAngle

@dataclass
class TRS:
    position: Vec3 = Vec3()
    rotation: QuaternionAngle = QuaternionAngle()
    scale: Vec3 = Vec3()