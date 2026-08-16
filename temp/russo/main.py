import math
import sweet as sw
from sweet.core.linalg.vector import Vec3

import glm
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
assets2 = sw.Assets.load_assets(r"temp\russo\progress.glb")

obj = sw.Entity("obj")
# print(assets.meshes)
scene = sw.Scene("scene")
first_key = list(assets.meshes.values())[0][0]
sec_key = list(assets.materials.values())[0]
vis = sw.Visual(first_key, sec_key)
obj.scale = Vec3(1, 0.1, 1)
obj.position = Vec3(0, -1, 0)
# obj.attach_visual(vis)
# obj.attach_visual(sw.Visual(list(assets.meshes.values())[1][0], sec_key))
obj.attach_visual(sw.Visual(list(assets2.meshes.values())[0][0], sec_key))
scene.add_entity(obj)

# mrt = sw.Engine.gfx_device.create_mrt_framebuffer(1366 // 2, 768 - 300, [4, 4, 4], True)

class Player(sw.GameModel):
    def __init__(self, win: sw.WindowSurface, light: sw.gameplay.light.Light | None = None):
        self.camera = sw.Camera()
        self.camera.position = Vec3(0, 0, 3)
        self.light = light
        
        self.render = sw.View(sw.UpdatePolicy.EVERY_FRAME)
        self.render.set_target(win)
        self.render.set_scene(scene)
        self.render.activate()

        self.cam_rot = sw.core.linalg.rotation.EulerAngleXYZ()

        self.win = win

    def main(self):
        if self.win.input.is_key_held(sw.Key.W):
            self.node.position = Vec3(
                self.node.position.x - .01 * math.sin(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z - .01 * math.cos(self.cam_rot.y),
            )
        if self.win.input.is_key_held(sw.Key.S):
            self.node.position = Vec3(
                self.node.position.x + .01 * math.sin(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z + .01 * math.cos(self.cam_rot.y),
            )
        if self.win.input.is_key_held(sw.Key.A):
            self.node.position = Vec3(
                self.node.position.x - .01 * math.cos(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z + .01 * math.sin(self.cam_rot.y)
            )
        if self.win.input.is_key_held(sw.Key.D):
            self.node.position = Vec3(
                self.node.position.x + .01 * math.cos(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z - .01 * math.sin(self.cam_rot.y)
            )

        if self.win.input.is_key_held(sw.Key.LEFT_SHIFT):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y - 0.1,
                self.node.position.z
            )

        if self.win.input.is_key_held(sw.Key.SPACE):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y + 0.1,
                self.node.position.z
            )

        self.camera.position = self.node.position

        self.cam_rot.x += self.win.input.get_mouse_delta()[1] * 3.1415 / 180
        self.cam_rot.x = min(max(self.cam_rot.x, -3.1415 / 2), 3.1415 / 2)
        self.cam_rot.y += self.win.input.get_mouse_delta()[0] * 3.1415 / 180

        self.camera.rotation = self.cam_rot

        self.render.view = self.camera.view_matrix()
        self.camera.projection.aspect = self.win.size[0] / self.win.size[1]
        self.render.projection = self.camera.projection_matrix()

        if self.light:
            forward_raw = glm.vec3(self.camera.view_matrix()[2])
            forward_direction = -forward_raw
            light_dir = glm.normalize(forward_direction)
            self.light.direction = Vec3(light_dir.x, light_dir.y, light_dir.z)
            self.light.position = self.node.position

new_p1 = sw.Entity("car-los")
new_p2 = sw.Entity("car-los2")
new_p1.inherit_model(Player, win=win2)
new_p1.attach_visual(vis)

light = sw.gameplay.light.Light()
new_p2.inherit_model(Player, win=win1, light=light)
new_p2.add_light(light)
# new_p2.attach_visual(vis)
new_p1.position = Vec3(0, 0, 0.95)
new_p2.position = Vec3(0, 0, 0.95)

scene.add_entity(new_p1)
scene.add_entity(new_p2)
scene.activate()

sw.start()