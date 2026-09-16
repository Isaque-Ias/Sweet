import math
import sweet as sw
from sweet.core.linalg.vector import Vec3

sw.Engine.initialize(
    graphics_device=sw.GraphicsDevice.MODERNGL,
    display_modality=sw.DisplayModality.MODERNGL,
)

win1 = sw.Engine.create_window()
win1.initialize(width=1366, height=768, title="Window 1")
# win1.fullscreen = True

# assets = sw.Assets.load_assets(r"temp\russo\Untitled.glb")
assetsm1 = sw.Assets.load_scene(r"temp\russo\pbr_sphere.glb")
# assets2 = sw.Assets.load_assets(r"temp\russo\progress.glb")
# assets3 = sw.Assets.load_scene(r"temp\russo\scenario.glb")
# assets3 = sw.Assets.load_scene(r"temp\russo\scen.glb")
scene = sw.Scene("scene")
# first_key = list(assets.meshes.values())[0][0]
# sec_key = list(assetsm1[0].materials.values())[0]

# i = 0
# for asset in assets3[0].meshes.values():
#     i += 1
#     # if i > 1:
#     # break
#     tobj = sw.Entity(f"{i}ok")
#     tobj.position = tobj.position * .1
#     tobj.scale = tobj.scale * .1
#     for prim in asset:
#         vis = sw.Visual(prim, sec_key)
#         tobj.attach_visual(vis)
#     scene.add_entity(tobj)

# ent = sw.Entity("aaaa")
# ent.attach_visual(sw.Visual(list(assetsm1[0].meshes.values())[0][0], list(assetsm1[0].materials.values())[0]))
# ent.attach_visual(sw.Visual(list(assetsm1[0].meshes.values())[0][1], list(assetsm1[0].materials.values())[0]))
# ent.position = Vec3(0, 1, 0)
scene = assetsm1[1]
# for entity in assetsm1[1].entities:
#     ent = entity
#     scene.add_entity(ent)

class Player(sw.GameModel):
    def __init__(self, win: sw.WindowSurface):
        self.camera = sw.Camera()
        self.camera.projection.fov = 60
        self.camera.position = Vec3(0, 3, 0)

        self.render = sw.View(sw.UpdatePolicy.EVERY_FRAME)
        self.render.set_target(win)
        self.render.set_scene(scene)
        self.render.activate()

        self.cam_rot = sw.core.linalg.rotation.EulerAngleXYZ()

        self.win = win
        self.speed = 0.01
        self.k = 12
        self.acc = self.speed

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
                self.node.position.z + self.speed * math.sin(self.cam_rot.y),
            )
        if self.win.input.is_key_held(sw.Key.D):
            self.node.position = Vec3(
                self.node.position.x + self.speed * math.cos(self.cam_rot.y),
                self.node.position.y,
                self.node.position.z - self.speed * math.sin(self.cam_rot.y),
            )

        if self.win.input.is_key_held(sw.Key.F):
            self.k += 0.01
            skbx.update(time=self.k * 1000)

        if self.win.input.is_key_held(sw.Key.G):
            self.k -= 0.01
            skbx.update(time=self.k * 1000)

        if self.win.input.is_key_held(sw.Key.LEFT_SHIFT):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y - self.acc,
                self.node.position.z,
            )

        if self.win.input.is_key_held(sw.Key.SPACE):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y + self.acc,
                self.node.position.z,
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
new_p1.position = Vec3(0, 3, 0)
light = sw.gameplay.light.Light()
light.position = Vec3(0, 100, -100)
light.direction = Vec3(0, -1, 1)
new_p1.inherit_model(Player, win=win1)
# first_key = list(assets.meshes.values())[0][0]
# sec_key = list(assets.materials.values())[0]
# vis = sw.Visual(first_key, sec_key)
# new_visual = sw.Visual(list(assets.meshes.values())[0][0], sec_key)
# new_p1.attach_visual(new_visual)
new_p1.add_light(light)

scene.add_entity(new_p1)

# cb = sw.plataform.hal.opengl.mgl.gfx_device.create_cubemap_framebuffer(win1.size[0], [4], 4, "f2")
# print(cb.get_target())
skbx = sw.gameplay.skybox.NishitaSkyBox()
scene.skybox = skbx
skbx.update(time=18000)

# dummy_volume_configs = [
#     # {
#     #     "invWorldMatrix": np.identity(4, dtype=np.float32),
#     #     "boundsMin": (-20.0, -10.0, -20.0),
#     #     "boundsMax": (20.0, 10.0, 20.0),
#     #     "densityScale": 0.85,
#     #     "absorption": 0.05,
#     #     "scatteringColor": (0.9, 0.95, 1.0, 1.0),  # Slightly bluish fog
#     #     "noiseHandle": (1, 0)                       # Bindless texture handle for 3D noise
#     # },
#     {
#         "invWorldMatrix": np.identity(4, dtype=np.float32),
#         "boundsMin": (0.0, 0.0, 0.0),
#         "boundsMax": (100.0, 50.0, 100.0),
#         "densityScale": 1.5,
#         "absorption": 0.2,
#         "scatteringColor": (1.0, 0.8, 0.6, 1.0),  # Warm/dense fog
#         "noiseHandle": (2, 0)
#     }
# ]
# volume_source = UploadManager.upload_volumes(dummy_volume_configs, max_capacity=16)

scene.activate()

sw.start()
