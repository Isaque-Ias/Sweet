from enum import Enum, auto
import glm
from dataclasses import dataclass
from abc import ABC
from ..core.linalg.rotation import Rotation, RotationModel, QuaternionAngle
from ..core.linalg.vector import Vec3

class Projection(ABC):
    pass

class CameraMode(Enum):
    PERSPECTIVE = auto()
    ORTHOGRAPHIC = auto()

@dataclass
class Perspective(Projection):
    fov: float
    aspect: float
    near: float
    far: float

@dataclass
class Orthographic(Projection):
    xmag: float
    ymag: float
    near: float
    far: float

class Camera:
    def __init__(self, position: Vec3 = Vec3(0, 0, 0), rotation: Rotation = QuaternionAngle(), projection: Projection | None = None):
        self.position = position
        self.rotation = rotation

        if projection:
            self.projection = projection
        else:
            self.projection: Projection = Perspective(
                fov = 60.0,
                aspect = 1366 / 768,
                near = 0.001,
                far = 1000.0
            )

        self.camera_mode = CameraMode.PERSPECTIVE

    def view_matrix(self) -> glm.mat4x4:
        transform = glm.translate(glm.mat4(1), self.position.unp()) # type: ignore
        x, y, z, w = self.rotation.convert(RotationModel.QUATERNION).scalars
        quat = glm.quat(w, x, y, z)
        transform *= glm.mat4_cast(quat) # type: ignore
        return glm.inverse(transform) # type: ignore

    def projection_matrix(self) -> glm.mat4x4:
        if self.camera_mode == CameraMode.PERSPECTIVE and isinstance(self.projection, Perspective):
            return glm.perspective( # type: ignore
                glm.radians(self.projection.fov), # type: ignore
                self.projection.aspect,
                self.projection.near,
                self.projection.far
            )
        
        elif self.camera_mode == CameraMode.ORTHOGRAPHIC and isinstance(self.projection, Orthographic):
            return glm.ortho( # type: ignore
                -self.projection.xmag,
                self.projection.xmag,
                -self.projection.ymag,
                self.projection.ymag,
                self.projection.near,
                self.projection.far
            )

        return glm.mat4(1)