from enum import Enum, auto
from sweet.core.linalg.vector import Vec3
import glm

class LightType(Enum):
    POINT = auto()
    DIRECTIONAL = auto()
class Light:
    def __init__(self, light_type: LightType = LightType.POINT, direction: Vec3 = Vec3(1, 0, 0)):
        self.type = light_type
        self.color = (1.0, 1.0, 1.0)
        self.intensity = 1.0
        self.direction = direction.normalize()
        self.position = Vec3(0, 0, 0)
        self.fov = 90

    def get_view(self):
        dir_glm = glm.vec3(self.direction.x, self.direction.y, self.direction.z)
        
        if abs(dir_glm.y) > 0.9999:
            up_reference = glm.vec3(0, 0, 1)
        else:
            up_reference = glm.vec3(0, 1, 0)

        orientacao = glm.quatLookAt(dir_glm, up_reference) # type: ignore

        up = orientacao * glm.vec3(0, 1, 0)

        target = glm.vec3(self.position.x + self.direction.x,
                          self.position.y + self.direction.y,
                          self.position.z + self.direction.z)

        return glm.lookAt(self.position.unp(), target, up) # type: ignore

    def get_projection(self):
        if self.type == LightType.POINT:
            return glm.ortho(-200.0, 200.0, -200.0, 200.0, -100.0, 300.0)#glm.perspective(self.fov * 3.1415 / 180, 1, 1, 100) # type: ignore
            return glm.perspective(self.fov * 3.1415 / 180, 1, .1, 500) # type: ignore