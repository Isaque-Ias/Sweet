import struct
import math
from typing import Any, Optional, Union
import sweet as sw
from sweet.core.linalg.vector import Vec3
import numpy as np
import moderngl 
from PIL import Image

sw.Engine.initialize(
    graphics_device=sw.GraphicsDevice.MODERNGL,
    display_modality=sw.DisplayModality.MODERNGL
)

win1 = sw.Engine.create_window()
win1.initialize(width=1366, height=768, title="Window 1")
# win1.fullscreen = True

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
        self.camera.position = Vec3(0, 3, 0)
        
        self.render = sw.View(sw.UpdatePolicy.EVERY_FRAME)
        self.render.set_target(win)
        self.render.set_scene(scene)
        self.render.activate()

        self.cam_rot = sw.core.linalg.rotation.EulerAngleXYZ()

        self.win = win
        self.speed = .1
        self.k = 0.025
        self.acc = 1

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
            self.k += 0.01

        if self.win.input.is_key_held(sw.Key.G):
            self.k -= 0.01

        if self.win.input.is_key_held(sw.Key.Y):
            self.acc *= 1.1

        if self.win.input.is_key_held(sw.Key.U):
            self.acc *= .9

        if self.win.input.is_key_held(sw.Key.V):
            light.near *= 1.1
            print(light.near)

        if self.win.input.is_key_held(sw.Key.B):
            light.near *= .9
            print(light.near)

        if self.win.input.is_key_held(sw.Key.N):
            light.far *= 1.1
            print(light.far, "far")

        if self.win.input.is_key_held(sw.Key.M):
            light.far *= .9
            print(light.far, "far")

        if self.win.input.is_key_held(sw.Key.Q):
            my_view.projection = self.camera.projection_matrix()
            my_view.view = self.camera.view_matrix()
            my_view.add_demand()

        sw.graphics.render.process.PipelineManager.day_time = self.k
        sw.graphics.render.process.PipelineManager.set_uniform_value("sw_SunIntensity", struct.pack("3f", self.acc, self.acc, self.acc)) 

        if self.win.input.is_key_held(sw.Key.LEFT_SHIFT):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y - self.acc,
                self.node.position.z
            )

        if self.win.input.is_key_held(sw.Key.SPACE):
            self.node.position = Vec3(
                self.node.position.x,
                self.node.position.y + self.acc,
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
light.position = Vec3(0, 100, -100)
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

# skbx = sw.gameplay.skybox.SkyBox(sw.gameplay.skybox.SkyBoxType.NISHITA)
# scene.skybox = skbx
# skbx.update(time=0)

mrt = sw.plataform.hal.opengl.mgl.gfx_device.create_mrt_framebuffer(win1.size[0], win1.size[1], color_formats=[4, 4], has_depth=True)
my_view = sw.View(sw.UpdatePolicy.ON_DEMAND)
my_view.set_target(mrt)
my_view.set_scene(scene)
my_view.set_viewport((0, 0, win1.size[0], win1.size[1]))

sw.graphics.render.process.PipelineManager.process_views([my_view])
my_view._target.native_handle


_MGL_DTYPE_TO_NUMPY: dict[str, Any] = {
    'f1': np.uint8,
    'f2': np.float16,
    'f4': np.float32,
    'u1': np.uint8,
    'u2': np.uint16,
    'u4': np.uint32,
    'i1': np.int8,
    'i2': np.int16,
    'i4': np.int32,
}

_CUBE_FACE_NAMES = ["posx", "negx", "posy", "negy", "posz", "negz"]

def save_image(filename: str, target, attachment: Optional[int] = None):
    colors = getattr(target, "color_textures", None)
    
    if attachment is None:
        channels = len(target.color_textures)  # type: ignore
        for i in range(channels):
            _save_attachment_image(target.native_handle(), i, f"{filename}_{i}.png")  # type: ignore
        _save_attachment_image(target.native_handle(), -1, f"{filename}_depth.png")  # type: ignore
    else:
        _save_attachment_image(target.native_handle(), attachment, filename + ".png")  # type: ignore

def _save_attachment_image(
        fbo: Any,
        attachment_index: Union[int, str],
        filename: str,
        near: float = 0.1,
        far: float = 100.0,
    ):
        width, height = fbo.size
        is_depth = attachment_index in (-1, "depth")

        if is_depth:
            raw_bytes = fbo.read(
                viewport=(0, 0, width, height),
                components=1,
                attachment=-1,
                dtype="f4",
            )

            depth_data = np.frombuffer(raw_bytes, dtype=np.float32).reshape(
                (height, width)
            )

            depth_data = (2.0 * near * far) / (
                far + near - (2.0 * depth_data - 1.0) * (far - near)
            )
            depth_data = (depth_data - near) / (far - near)

            depth_grayscale = (np.clip(depth_data, 0.0, 1.0) * 255.0).astype(
                np.uint8
            )

            img = Image.fromarray(depth_grayscale, mode="L")

        else:
            idx = int(attachment_index)
            if len(fbo.color_attachments) <= idx:
                return

            attachment_texture = fbo.color_attachments[idx]

            channels = attachment_texture.components
            texture_dtype = attachment_texture.dtype

            raw_bytes = fbo.read(
                viewport=(0, 0, width, height),
                components=channels,
                attachment=idx,
            )

            # Parse buffer into normalized uint8 array regardless of dtype
            if "4" in texture_dtype:
                np_data = np.frombuffer(raw_bytes, dtype=np.float32)
                np_data = (np.clip(np_data, 0.0, 1.0) * 255.0).astype(np.uint8)
            else:
                np_data = np.frombuffer(raw_bytes, dtype=np.uint8)

            # Reshape into (height, width, channels)
            if channels == 1:
                parsed = np_data.reshape((height, width))
            else:
                parsed = np_data.reshape((height, width, channels))

            # Build output image based on channel count
            if channels == 1:
                # Single channel -> (R, R, R, 255)
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                rgba[..., 0] = parsed
                rgba[..., 1] = parsed
                rgba[..., 2] = parsed
                rgba[..., 3] = 255
                img = Image.fromarray(rgba, mode="RGBA")

            elif channels == 2:
                # Two channels -> (R, G, 0, 255)
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                rgba[..., 0] = parsed[..., 0]
                rgba[..., 1] = parsed[..., 1]
                rgba[..., 2] = 0
                rgba[..., 3] = 255
                img = Image.fromarray(rgba, mode="RGBA")

            elif channels == 3:
                img = Image.fromarray(parsed, mode="RGB")

            elif channels == 4:
                img = Image.fromarray(parsed, mode="RGBA")

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # type: ignore
        img.save(filename)

scene.activate()

my_view.activate()

my_view.add_demand()
save_image("output_image", my_view.get_target()[0], attachment=None)  # Save all attachments

sw.start()
