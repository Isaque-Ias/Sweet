from abc import ABC, abstractmethod
import glm
from ...core.linalg.vector import Vec3
from ..camera import Camera

class ViewProvider(ABC):
    @abstractmethod
    def matrix(self) -> glm.mat4:
        pass

class ProjectionProvider(ABC):
    @abstractmethod
    def matrix(self) -> glm.mat4:
        pass

class CameraProvider(ABC):
    def __init__(self, camera: Camera):
        self.camera = camera

    def matrix(self) -> glm.mat4:
        return glm.mat4(self.camera.projection_matrix() * self.camera.view_matrix())

class LookAtView(ViewProvider):
    def __init__(self, eye: Vec3, target: Vec3, up: Vec3 = Vec3(0,1,0)):
        self.eye = eye.unp()
        self.target = target.unp()
        self.up = up.unp()

    def matrix(self):
        return glm.lookAt( # type: ignore
            self.eye,
            self.target,
            self.up
        )

class MatrixView(ViewProvider):
    def __init__(self, matrix: glm.mat4x4):
        self._matrix = matrix

    def matrix(self):
        return self._matrix

    def set_matrix(self, matrix: glm.mat4x4):
        self._matrix = matrix

class PerspectiveProjection(ProjectionProvider):
    def __init__(self,
                 fov: float,
                 aspect: float,
                 near: float,
                 far: float):
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far

    def matrix(self):
        return glm.perspective( # type: ignore
            glm.radians(self.fov), # type: ignore
            self.aspect,
            self.near,
            self.far
        )

class OrthographicProjection(ProjectionProvider):
    def __init__(self,
                 left: float,
                 right: float,
                 bottom: float,
                 top: float,
                 near: float,
                 far: float):
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top
        self.near = near
        self.far = far

    def matrix(self):
        return glm.ortho( # type: ignore
            self.left,
            self.right,
            self.bottom,
            self.top,
            self.near,
            self.far
        )

class MatrixProjection(ProjectionProvider):
    def __init__(self, matrix: glm.mat4x4):
        self._matrix = matrix

    def matrix(self):
        return self._matrix

    def set_matrix(self, matrix: glm.mat4x4):
        self._matrix = matrix