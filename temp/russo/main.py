import math
import sweet as sw
from sweet.core.linalg.vector import Vec3

sw.Engine.initialize(
    graphics_device=sw.GraphicsDevice.MODERNGL,
    display_modality=sw.DisplayModality.MODERNGL
)

win1 = sw.Engine.create_window()
win1.position = (0, 150)

win2 = sw.Engine.create_window()
win1.initialize(width=1366 // 2, height=768 - 300, title="Window 1")
win2.initialize(width=1366 // 2, height=768 - 300, title="Window 2")
win2.position = (1366 // 2, 150)

assets = sw.Assets.load_assets(r"temp\russo\Untitled.glb")

obj = sw.Entity("obj")
# print(assets.meshes)
scene = sw.Scene("scene")
first_key = list(assets.meshes.values())[0][0]
sec_key = list(assets.materials.values())[0]

vis = sw.Visual(first_key, sec_key)
obj.attach_visual(vis)
scene.add_entity(obj)

# mrt = sw.Engine.gfx_device.create_mrt_framebuffer(1366 // 2, 768 - 300, [4, 4, 4], True)

class Player(sw.GameModel):
    def __init__(self, win):
        self.camera = sw.Camera()
        self.camera.position = Vec3(0, 0, 3)
        
        self.render = sw.View(sw.UpdatePolicy.EVERY_FRAME)
        self.render.set_target(win)
        self.render.set_viewport((0, 0, 1366 // 2, 768 - 300))
        self.render.set_scene(scene)
        self.render.activate()

        self.cam_rot = sw.core.linalg.rotation.Rotation(model=sw.core.linalg.rotation.RotationModel.EULER_XYZ)

        self.win = win

    def main(self):
        if self.win.input.is_key_held(sw.Key.W):
            self.node.position = sw.core.linalg.vector.Vec3(
                self.node.position.x - .01 * math.sin(self.camera.rotation.values[1]),
                self.node.position.y,
                self.node.position.z - .01 * math.cos(self.camera.rotation.values[1]),
            )
        if self.win.input.is_key_held(sw.Key.S):
            self.node.position = sw.core.linalg.vector.Vec3(
                self.node.position.x + .01 * math.sin(self.camera.rotation.values[1]),
                self.node.position.y,
                self.node.position.z + .01 * math.cos(self.camera.rotation.values[1]),
            )
        if self.win.input.is_key_held(sw.Key.A):
            self.node.position = sw.core.linalg.vector.Vec3(
                self.node.position.x - .01 * math.cos(self.camera.rotation.values[1]),
                self.node.position.y,
                self.node.position.z + .01 * math.sin(self.camera.rotation.values[1])
            )
        if self.win.input.is_key_held(sw.Key.D):
            self.node.position = sw.core.linalg.vector.Vec3(
                self.node.position.x + .01 * math.cos(self.camera.rotation.values[1]),
                self.node.position.y,
                self.node.position.z - .01 * math.sin(self.camera.rotation.values[1])
            )

        self.camera.position = self.node.position

        self.cam_rot.values[0] += self.win.input.get_mouse_delta()[1] * 3.1415 / 180 * 5
        self.cam_rot.values[1] += self.win.input.get_mouse_delta()[0] * 3.1415 / 180 * 5

        self.camera.rotation = self.cam_rot

        self.render.view = self.camera.view_matrix()
        self.render.projection = self.camera.projection_matrix()

new_p1 = sw.Entity("car-los")
new_p2 = sw.Entity("car-los2")
new_p1.inherit_model(Player, win=win2)
new_p1.attach_visual(vis)

new_p2.inherit_model(Player, win=win1)
new_p2.attach_visual(vis)

scene.add_entity(new_p1)
scene.add_entity(new_p2)
scene.activate()

sw.start()