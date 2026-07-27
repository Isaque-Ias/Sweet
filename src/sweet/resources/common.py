from dataclasses import dataclass
from ..core.linalg.vector import Vec3
from ..core.linalg.rotation import Rotation

@dataclass
class TRS:
    position: Vec3 = Vec3()
    rotation: Rotation = Rotation()
    scale: Vec3 = Vec3()