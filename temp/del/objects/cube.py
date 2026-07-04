import sweet as sw
from objects.sandbox_object import SandboxObject


class Cube(SandboxObject):
    def __init__(
        self,
        pos: sw.Vec3 = sw.Vec3(0, 0, 0),
        parent: SandboxObject | None = None,
    ):
        super().__init__(pos, parent)

        self.texture = sw.Resources.texture("cube")
        self.model = sw.Resources.model("cube")


class WalkingCube(Cube):
    def __init__(
        self,
        pos: sw.Vec3 = sw.Vec3(0, 0, 0),
        parent: SandboxObject | None = None,
        speed: sw.Vec3 = sw.Vec3(0, 0, 0),
    ):
        super().__init__(pos, parent)

        self.speed: sw.Vec3 = speed

    def tick(self, dt: float):
        self.move(self.speed.x * dt, self.speed.y * dt, self.speed.z * dt)

        if self.pos.x > 5:
            sw.entity.EntityManager.agend_destroy(self)
