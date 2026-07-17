import sweet as sw


if __name__ == "__main__":
    window = sw.Window(title="oi", size=(1000, 100), pos=(100, 100))
    window.run()

# window = sw.Window(title="oi2", size=(100, 100))
# window.run()

# sw.init()
# sw.run()
# import math
# import sweet as sw
# from pathlib import Path
# from sweet.vector import Vec3
# from sweet.inputting import Input
# import numpy as np
# import moderngl

# sw.Display.resizable(True)
# screen_size = sw.Display.screen_size
# sw.Display.size((screen_size[0] - 100, screen_size[1] - 100))
# sw.Display.background((135, 206, 250, 255))

# sw.init()

# CWD = Path.cwd()
# PROJECT = CWD / "temp" / "russo"
# sw.System.set_config(PROJECT / "config" / "config.json")
# sw.Resources.load_assets(PROJECT / "assets.json")
# BUILD = CWD / "src" / "sweet" / "build"

# panini = sw.Shader.get("panini")
# panini_program = panini.program
# panini_frame = sw.Shader.new_fbo(screen_size, True)
# # panini_frame.texture.build_mipmaps()
# panini_frame.texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

# class Player(sw.Entity):
#     def __init__(self):
#         super().__init__((0, 0, 0))
#         self.pos: Vec3
#         self.camera_angle = Vec3(0, 0, 0)
#         self.mouse_x, self.mouse_y = Input.get_mouse_pos()
#         self.fov = 70
#         self.speed = 100
#         self.player_height = 1
#         self.velocity = Vec3(0, 0, 0)

#         self.third_person = True
#         self.cam_distance = 4.4
#         self.cam_height = 2.2
#         self.cam_shoulder = 1.66

#         self.texture = sw.Resources.texture("hand")
#         self.model = sw.Resources.model("hand")

#         Input.set_mouse_visibility(False)
#         Input.set_mouse_exclusivity(True)

#     def tick(self):
#         if Input.is_key_pressed(Input.key_code.F5):
#             self.third_person = not self.third_person
            
#         mouse_x, mouse_y = Input.get_mouse_pos()
#         mouse_dx = mouse_x - self.mouse_x
#         mouse_dy = mouse_y - self.mouse_y
#         self.mouse_x, self.mouse_y = mouse_x, mouse_y

#         self.camera_angle.x -= mouse_dx * 0.2
#         self.camera_angle.y += mouse_dy * 0.2
#         self.camera_angle.y = min(90, max(-90, self.camera_angle.y))

#         self.velocity.y -= 200 * sw.Time.delta()
#         self.pos += self.velocity * sw.Time.delta()

#         self.pos.y = max(self.pos.y, self.player_height)
#         if (
#             Input.is_key_pressed(Input.key_code.SPACE)
#             and self.pos.y <= self.player_height
#         ):
#             self.velocity.y = 100

#         yaw = math.radians(self.camera_angle.x)
#         pitch = math.radians(self.camera_angle.y)

#         if Input.is_key_held(Input.key_code.W):
#             self.pos.x -= math.sin(yaw) * self.speed * sw.Time.delta()
#             self.pos.z -= math.cos(yaw) * self.speed * sw.Time.delta()
#         if Input.is_key_held(Input.key_code.S):
#             self.pos.x += math.sin(yaw) * self.speed * sw.Time.delta()
#             self.pos.z += math.cos(yaw) * self.speed * sw.Time.delta()
#         if Input.is_key_held(Input.key_code.A):
#             self.pos.x -= math.cos(yaw) * self.speed * sw.Time.delta()
#             self.pos.z += math.sin(yaw) * self.speed * sw.Time.delta()
#         if Input.is_key_held(Input.key_code.D):
#             self.pos.x += math.cos(yaw) * self.speed * sw.Time.delta()
#             self.pos.z -= math.sin(yaw) * self.speed * sw.Time.delta()

#         if Input.is_key_held(Input.key_code.Q):
#             self.fov += 1
#         if Input.is_key_held(Input.key_code.E):
#             self.fov -= 1

#         if self.third_person:
#             right = Vec3(math.cos(yaw), 0, -math.sin(yaw))

#             look_dir = Vec3(
#                 math.sin(yaw) * math.cos(pitch),
#                 math.sin(pitch),
#                 math.cos(yaw) * math.cos(pitch),
#             )

#             cam_pos = self.pos
#             cam_pos += Vec3(0, self.cam_height, 0)
#             right_dist = right * self.cam_shoulder
#             back_dist = look_dir * self.cam_distance
#             cam_pos += right_dist + back_dist
#         else:
#             cam_pos = self.pos
#             cam_pos += Vec3(0, self.player_height, 0)

#         main_cam = sw.camera.CameraManager.get_main_camera()
#         main_cam.pos = cam_pos
#         main_cam.angle = self.camera_angle
#         main_cam.fov = self.fov

#     def draw(self):
#         if self.third_person:
#             sw.entity.Draw.draw_image(
#                 self.model,
#                 self.texture,
#                 self.transform,
#             )

# class Floor(sw.Entity):
#     def __init__(self):
#         super().__init__((0, -100, 0), scale=(100, 100, 100))
#         self.texture = sw.Resources.texture("pixel")
#         self.model = sw.Resources.model("forest")
#         quad_vbo = np.array([
#             -1.0,  1.0,#,    0.0, 1.0,
#             -1.0, -1.0,#,    0.0, 0.0,
#             1.0,  1.0,#,    1.0, 1.0,
#             1.0, -1.0,#,    1.0, 0.0,
#         ], dtype='f2')
#         self.f = 1

#         self.quad = sw.graphics.mesh.Mesh("instance", geometry=sw.common.Geometry(quad_vbo))
#         self.quad.upload()

#     def tick(self):
#         if sw.Input.is_key_held(sw.inputting.Input.key_code.H):
#             self.f -= 0.01
#         if sw.Input.is_key_held(sw.inputting.Input.key_code.Y):
#             self.f += 0.01

#     def draw(self):
#         global player
#         sw.Shader.ubo(0, "uCamPos", "3f", *((Vec3(1, 10, 1)).unp()))

#         sw.Draw.render(
#             self.model,
#             self.texture,
#             self.transform
#         )

# if __name__ == "__main__":
#     global player
#     player = Player()
#     Floor()
#     sw.run()
