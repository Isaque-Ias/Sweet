import sweet as sw


class SandboxObject(sw.Entity):
    # physics_body: PhysicsBody | None
    # selectable: bool = True
    # grabbable: bool = True
    # material: Material  # see section 3
    # spawn_id: str  # unique id for save/load and networking later

    def __init__(
        self,
        pos: sw.Vec3,
        parent: "SandboxObject | None" = None,
        tick: bool = False,
    ):
        super().__init__(
            (int(pos.x), int(pos.y), int(pos.z)),
            tick=tick,
        )
        self.pos: sw.Vec3  # This should not be needed
        self.parent: "SandboxObject | None" = parent
        self.children: list["SandboxObject"] = []
        if parent is not None:
            parent.children.append(self)

        self.model: sw.graphics.model.ModelInstance = sw.Resources.model("cube")
        self.texture: sw.graphics.texture.Imaging = sw.Resources.texture("cube")

    def draw(self):
        sw.entity.Draw.draw_image(
            self.model,
            self.texture,
            sw.Vec3(self.pos.x, self.pos.y, self.pos.z),
        )

    def move(self, dx: float, dy: float, dz: float):
        self.pos.x += dx
        self.pos.y += dy
        self.pos.z += dz

        for child in self.children:
            child.move(dx, dy, dz)
