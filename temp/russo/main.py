import math
import sweet as sw
from sweet.core.linalg.vector import Vec3

sw.Engine.initialize(
    graphics_device=sw.GraphicsDevice.MODERNGL,
    display_modality=sw.DisplayModality.MODERNGL
)

win1 = sw.Engine.create_window()
win1.initialize(width=1366, height=768, title="Window 1")
win1.fullscreen = True

assets = sw.Assets.load_assets(r"temp\russo\Untitled.glb")
assets2 = sw.Assets.load_assets(r"temp\russo\progress.glb")
assets3 = sw.Assets.load_scene(r"temp\russo\scenario.glb")

# print(assets.meshes)
scene = sw.Scene("scene")
# first_key = list(assets.meshes.values())[0][0]
# vis = sw.Visual(first_key, sec_key)
# obj.scale = Vec3(10, 0.1, 10)
# obj.position = Vec3(0, -1, 0)
sec_key = list(assets.materials.values())[0]
# obj = sw.Entity("obj")
# block_visual = sw.Visual(list(assets2.meshes.values())[0][0], sec_key)
# obj.attach_visual(block_visual)
# scene.add_entity(obj)

# for entity in assets3[1].entities:
#     scene.add_entity(entity)

i = 0
for asset in assets3[0].meshes.values():
    i += 1
    tobj = sw.Entity(f"{i}ok")
    for prim in asset:
        vis = sw.Visual(prim, sec_key)
        tobj.attach_visual(vis)
    scene.add_entity(tobj)

# obj2 = sw.Entity("obj2")
# obj2.scale = Vec3(1, 1, 1)
# obj2.position = Vec3(0, 0, 0)
# obj2.attach_visual(block_visual)
# scene.add_entity(obj2)
class Player(sw.GameModel):
    def __init__(self, win: sw.WindowSurface):
        self.camera = sw.Camera()
        self.camera.position = Vec3(0, 0, 3)
        
        self.render = sw.View(sw.UpdatePolicy.EVERY_FRAME)
        self.render.set_target(win)
        self.render.set_scene(scene)
        self.render.activate()

        self.cam_rot = sw.core.linalg.rotation.EulerAngleXYZ()

        self.win = win
        self.speed = .1
        self.k = 0.025

    def main(self):
        if self.win.input.is_key_held(sw.Key.W):
            self.node.position = Vec3(
                self.node.position.x - self.speed * math.sin(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z - self.speed * math.cos(self.cam_rot.y),
            )
        if self.win.input.is_key_held(sw.Key.S):
            self.node.position = Vec3(
                self.node.position.x + self.speed * math.sin(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z + self.speed * math.cos(self.cam_rot.y),
            )
        if self.win.input.is_key_held(sw.Key.A):
            self.node.position = Vec3(
                self.node.position.x - self.speed * math.cos(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z + self.speed * math.sin(self.cam_rot.y)
            )
        if self.win.input.is_key_held(sw.Key.D):
            self.node.position = Vec3(
                self.node.position.x + self.speed * math.cos(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z - self.speed * math.sin(self.cam_rot.y)
            )
        # sw.graphics.render.process.PipelineManager.set_uniform_value("sw_Radius", struct.pack("1f", self.k))

        
        if self.win.input.is_key_held(sw.Key.F):
            # skbx.update(time=0)
            self.k += 0.001

        if self.win.input.is_key_held(sw.Key.G):
            self.k -= 0.001 

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

new_p1 = sw.Entity("car-los")

light = sw.gameplay.light.Light()
light.position = Vec3(0, 100, -100) * 1.5
light.direction = Vec3(0, -1, 1)
# light.position = Vec3(-156.61053068371038, 102.99999999999842, -104.69650543140432)
# light.direction = Vec3(1, 0, 1)
new_p1.inherit_model(Player, win=win1)
first_key = list(assets.meshes.values())[0][0]
sec_key = list(assets.materials.values())[0]
vis = sw.Visual(first_key, sec_key)
new_visual = sw.Visual(list(assets.meshes.values())[0][0], sec_key)
# new_p1.attach_visual(new_visual)
new_p1.add_light(light)

scene.add_entity(new_p1)

scene.activate()

sw.start()

# skbx = sw.gameplay.skybox.SkyBox(sw.gameplay.skybox.SkyBoxType.NISHITA)
# scene.skybox = skbx