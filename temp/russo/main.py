from chunk import *
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

assetsm1 = sw.Assets.load_scene(r"temp\russo\pbr_sphere.glb")
scene = assetsm1[1]

material = list(assetsm1[0].materials.values())[0]
sw.graphics.upload.UploadManager.update_material_factors(material, clearcoat_factor=0)

mat = sw.PBRMaterial("matt")
mat.base_color_factor = [1, 1, 1, 1]
mat.clearcoat_factor = 1
mat.emissive_factor = [0, 0, 0]
mat.metallic_factor = 0
mat.roughness_factor = 1
mat.specular_factor = 0
mat.clearcoat_roughness_factor = 0
mat.upload()

mat2 = sw.PBRMaterial("matt2")
mat2.base_color_factor = [0.96 * .2, 0.94 * .2, 0.86 * .2, 1]
mat2.clearcoat_factor = 0
mat2.emissive_factor = [0, 0, 0]
mat2.metallic_factor = 0
mat2.roughness_factor = 1
mat2.specular_factor = 0
mat2.clearcoat_roughness_factor = 1
mat2.upload()

visual = sw.Visual(list(assetsm1[0].meshes.values())[0][0], mat.source_material)

ent = sw.Entity("aa")
ent.attach_visual(visual)
ent.position = Vec3(1, 0, 0)
# scene.add_entity(ent)

generate_procedural_eye(scene, mat.source_material, mat2.source_material)

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
        self.speed = 0.5
        self.k = 6
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

import numpy as np

def make_inv_transform(position, scale):
    # Scale matrix
    S = np.diag([scale[0], scale[1], scale[2], 1.0])
    # Translation matrix
    T = np.identity(4)
    T[:3, 3] = position
    
    # World matrix = Translation * Scale
    world_matrix = T @ S
    # Invert to transform World space -> Local [-1, 1] space
    return np.linalg.inv(world_matrix).astype(np.float32)

volume_data = [
    # {
    #     "type": 0,                             # VOLUME_TYPE_GLOBAL_HEIGHT
    #     "color": (0.8, 0.85, 0.9, 0.05),       # Tint (RGB) + Base Density (A)
    #     "phase_g": 0.2,                        # Mild forward scattering
    #     "height_falloff": 0.15,               # Density drops with height
    #     "ground_level": 0.0,                   # Fog starts at Y = 0.0
    #     "absorption": 0.01,                    # Light attenuation
    # },
    
    # Volume 1: Box-bounded Fog (e.g., localized smoke in a room)
#     {
#     "type": 1,  # VOLUME_TYPE_BOX
#     "inv_transform": make_inv_transform(
#         position=(0.0, 2.5, 0.0), 
#         scale=(50.0, 50.0, 50.0)      # Compact 5x5x5 box
#     ),
#     "color": (0.95, 0.95, 1.0, 0.8),   # Lowered alpha from 4.0 -> 0.8 so it's translucent, not a solid block
#     "phase_g": 0.4,                    
#     "absorption": 0.1,                 
#     "cloud_params": (
#         1.5,   # detail_scale: keeps features large enough to look like a cloud inside 5 units
#         0.2,   # anim_speed
#         0.25,  # soft_edge: broader feathering so close-up views don't show flat sides
#         0.0
#     )
# }
    # Volume 2: Spherical Fog (e.g., localized magical orb or aura)
    # {
    #     "type": 2,                             # VOLUME_TYPE_SPHERE
    #     "inv_transform": make_inv_transform(
    #         position=(-4.0, 1.0, 12.0), 
    #         scale=(2.5, 2.5, 2.5)              # Radius = 2.5 units
    #     ),
    #     "color": (0.1, 0.9, 0.4, 0.8),         # Glowing green tint
    #     "phase_g": -0.3,                       # Backwards scattering
    #     "height_falloff": 0.0,
    #     "ground_level": 0.0,
    #     "absorption": 0.05,
    # }
]

from sweet.graphics.upload import UploadManager
gpu_source = UploadManager.upload_volumes(
    volume_configs=volume_data,
    max_capacity=16
)

print(f"Uploaded {gpu_source.volume_count} volumes successfully.")
print(f"SSBO Buffer View Index: {gpu_source.volume_view.buffer_index}")

scene.activate()

sw.start()
