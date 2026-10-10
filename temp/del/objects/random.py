import sweet as sw
from sweet.core.linalg.vector import Vec3
from sweet.inputting import Input


class Floor(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 0))
        self.pos = Vec3(0, 0, 0)

        self.texture = sw.Resources.texture("floor")
        self.model = sw.Resources.model("floor")

    def draw(self):
        sw.entity.Draw.draw_image(
            self.model,
            self.texture,
            Vec3(self.pos.x, self.pos.y, self.pos.z),
            Vec3(1000, 1, 1000),
        )


class Airplane(sw.Entity):
    def __init__(self):
        super().__init__((0, 0, 0))
        self.pos = Vec3(0, 0, 0)

        self.texture = sw.Resources.texture("airplane")
        self.model = sw.Resources.model("airplane")

    def tick(self, dt: float):
        if Input.is_key_held(Input.key_code.I):
            self.pos.y -= 1
        if Input.is_key_held(Input.key_code.J):
            self.pos.x -= 1
        if Input.is_key_held(Input.key_code.K):
            self.pos.y += 1
        if Input.is_key_held(Input.key_code.L):
            self.pos.x += 1
        if Input.is_key_held(Input.key_code.N):
            self.pos.z += 1
        if Input.is_key_held(Input.key_code.M):
            self.pos.z -= 1

    def draw(self):
        sw.entity.Draw.draw_image(
            self.model,
            self.texture,
            Vec3(self.pos.x, self.pos.y, self.pos.z),
        )


class Cube(sw.Entity):
    def __init__(self, pos: Vec3 = Vec3(0, 0, 0)):
        super().__init__((0, 0, 0))
        self.pos = pos

        self.texture = sw.Resources.texture("cube")
        self.model = sw.Resources.model("cube")

    def draw(self):
        sw.entity.Draw.draw_image(
            self.model,
            self.texture,
            Vec3(self.pos.x, self.pos.y, self.pos.z),
        )


class CubeMatrix(sw.Entity):
    def __init__(self, pos: Vec3 = Vec3(0, 0, 0), size: int = 8):
        super().__init__((0, 0, 0))
        self.pos = pos

        self.size = size
        self.gap = 2

        self.texture = sw.Resources.texture("cube")
        self.model = sw.Resources.model("cube")

    def tick(self, dt: float):
        if Input.is_key_held(Input.key_code.R):
            self.size = min(16, self.size + 1)
        if Input.is_key_held(Input.key_code.F):
            self.size = max(1, self.size - 1)

    def draw(self):
        for x in range(-self.size, self.size + 1):
            for y in range(-self.size, self.size + 1):
                for z in range(-self.size, self.size + 1):
                    pos = Vec3(
                        self.pos.x + x * (self.gap + 1),
                        self.pos.y + y * (self.gap + 1),
                        self.pos.z + z * (self.gap + 1),
                    )
                    sw.entity.Draw.draw_image(
                        self.model,
                        self.texture,
                        pos,
                    )
