# import sweet as sw
# from sweet.entity import *
# from sweet.inputting import *
# from sweet.graphics.texture import *
# from pathlib import Path
# from pygame.locals import *
# from math import pi

# SOURCE = Path.cwd() / "src" / "sources"
# sw.looping.GameLoop.set_screen_size((sw.looping.GameLoop.view_width, sw.looping.GameLoop.view_height))
# main_cam = sw.camera.Camera.get_main_camera()
# view_size = Vec2(480, 270)
# cam_factor = (view_size.y / sw.looping.GameLoop.view_height)
# main_cam.set_scale((cam_factor, cam_factor))

# sw.looping.GameLoop.set_background_color((255, 230, 147, 1))

# ShaderManager.add_shader_file("floor", {"vao": [
#     ("iPos", 2),
#     ("iScale", 2),
#     ("iRot", 2),
#     ("iUVOff", 2),
#     ("iUVScale", 2),
#     ("iRgb", 3),
#     ("iAlpha", 1),
#     ("iView", 2),
#     ("iNPos", 3),
#     ("iNScale", 3),
#     ("iNRot", 3),
#     ]
# })
# ShaderManager.add_shader_file("def3d", EntityTools.get_default_3d_shader_layout())
# sw.init()

# Texture.set_texture("PlayerBody", SOURCE / "player_body.png").upload()
# Texture.set_texture("PlayerLeg", SOURCE / "player_leg.png").upload()
# Texture.set_texture("pixel", SOURCE / "build" / "pixel.png").upload()
# Texture.set_texture("churchglass", SOURCE / "churchglass.png").upload()
# Texture.set_texture("churchwall", SOURCE / "churchwall.png").upload()
# Texture.set_texture("frontlane", SOURCE / "frontlane.png").upload()
# Texture.set_texture("churchlight", SOURCE / "light.png").upload()
# Texture.set_texture("vignette", SOURCE / "vignette.png").upload()
# Texture.set_texture("frontline", SOURCE / "frontline.png").upload()
# Texture.set_texture("ground", SOURCE / "floor.png").upload()
# Texture.set_texture("ground_l", SOURCE / "floor2.png").upload()

# grv = 10 / 60

# class Player(Entity):
#     def __init__(self, pos):
#         super().__init__(pos, order=5, tick=True)
#         self.spr_body = Texture.get_texture("PlayerBody")
#         self.spr_legs = Texture.get_texture("PlayerLeg")
#         self.size = .05
#         self.scale = Vec(self.spr_body.get_width() * self.size, self.spr_body.get_height() * self.size)
        
#         vertices = [Vec(self.scale.x / 2, 0).rotate(angle * 360 / 15) for angle in range(15)]

#         self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))

#         self.jump_power = 4
#         self.speed = 36 / 60
#         self.velocity = Vec(0, 0)
#         self.floor_collision = False
#         self.right_grip = False
#         self.left_grip = False

#         self.jumped = False

#         self.current_pos = Vec(0, 0)
#         self.offset = Vec(0, -30)

#     def tick(self):
#         self.velocity.y += grv
#         self.velocity.x *= 0.8

#         self.pos += self.velocity

#         if Input.get_press(K_a):
#             self.velocity.x -= self.speed
#         if Input.get_press(K_d):
#             self.velocity.x += self.speed

#         if Input.get_press(K_SPACE) and not self.jumped:
#             if self.floor_collision:
#                 self.velocity.y = -self.jump_power
#                 self.jumped = True
#             elif self.left_grip:
#                 self.velocity.y = -self.jump_power
#                 self.velocity.x = self.jump_power
#                 self.jumped = True
#             elif self.right_grip:
#                 self.velocity.y = -self.jump_power
#                 self.velocity.x = -self.jump_power
#                 self.jumped = True

#         if Input.get_released(K_SPACE):
#             self.jumped = False
            
#         self.floor_collision = False
#         self.right_grip = False
#         self.left_grip = False
#         def response(entity, other, data):
#             entity.pos += data.mtv * (data.is_b * 2 - 1)
#             parallel = Vec(data.mtv.y, -data.mtv.x)
#             parallel_magnitude = parallel.magnitude_squared()
#             if parallel.cross(entity.velocity) > 0:
#                 entity.velocity = parallel * parallel.dot(entity.velocity) / parallel_magnitude

#             if data.mtv.x == 0:
#                 if data.mtv.y > 0:
#                     self.floor_collision = True
#             else:
#                 if abs(data.mtv.y / data.mtv.x) > 1 and data.mtv.y > 0:
#                     self.floor_collision = True

#             if data.mtv.y == 0:
#                 if data.mtv.x > 0:
#                     self.right_grip = True
#                 else:
#                     self.left_grip = True

#                 self.velocity.y *= 0.7

#         sw.linalg.collision.Collision.collision_list(self, Block, apply_func=response)

#         goal_pos = self.pos - view_size / 2 + self.offset
#         self.current_pos += (goal_pos - self.current_pos) / 10
#         main_cam.set_pos(self.current_pos.unp())

#     def draw(self):
#         pass
#         # EntityTools.draw_image(self.spr_body, self.pos.unp(), self.scale.unp(), color=(127, 127, 127))
#         # EntityTools.draw_image_3d(self.spr_body, (*self.pos.unp(), -1), (*self.scale.unp(), 1), color=(127, 127, 127), program="def3d")
#         # EntityTools.draw_image_3d(self.spr_body, (*self.pos.mirror_y().unp(), -1), (40, 40, 1), (0, 0, 0), offset=(0, -300), color=(127, 127, 127), program="def3d")

# class Block(Entity):
#     def __init__(self, pos, size=(100, 100), angle=0):
#         super().__init__(pos, image=Texture.get_texture("pixel"), scale=size, angle=angle, order=5)
#         vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]
#         self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))
#         self.mask.polygons["main"] = self.mask.get_polygon("main").rotate(self.angle)

#     def draw(self):
#         pass
#         # EntityTools.draw_image(self.image, self.pos.unp(), self.scale.unp(), self.angle, color=(127, 127, 127))

# def parallax(size, pos, rate):
#     camera_pos = Vec(*main_cam.get_pos())
#     position = Vec(camera_pos.x * rate, -size.y / 2) + pos
#     return position

# class Background(Entity):
#     def __init__(self):
#         super().__init__((0, 0), order=2)
#         self.front_background = Texture.get_texture("frontlane")
#         blend = (100, 66, 47)
#         factor = .2
#         self.front_background.set_image(self.front_background.apply_channels(self.front_background.get_image(),
#                                              lambda x: x * (1 - factor) + blend[0] * factor,
#                                              lambda x: x * (1 - factor) + blend[1] * factor,
#                                              lambda x: x * (1 - factor) + blend[2] * factor, lambda x: x))
#         self.front_background.upload()
#         self.front_bg_size = (self.front_background.get_width(), self.front_background.get_height())
#         self.back_background = Texture.get_texture("churchwall")
#         blend = (100, 66, 47)
#         factor = .33
#         self.back_background.set_image(self.back_background.apply_channels(self.back_background.get_image(),
#                                              lambda x: x * (1 - factor) + blend[0] * factor,
#                                              lambda x: x * (1 - factor) + blend[1] * factor,
#                                              lambda x: x * (1 - factor) + blend[2] * factor, lambda x: x))
#         self.back_background.upload()
#         self.back_bg_size = (self.back_background.get_width(), self.back_background.get_height())
#         self.ground = Texture.get_texture("ground")
#         self.ground_size = (self.ground.get_width(), self.ground.get_height())
#         self.ground_layer = Texture.get_texture("ground_l")
#         self.layer_size = (self.ground_layer.get_width(), self.ground_layer.get_height())
#         self.back_background_glass = Texture.get_texture("churchglass")
#         self.back_background_light = Texture.get_texture("churchlight")
#         self.back_light_size = (self.back_background_light.get_width(), self.back_background_light.get_height())
#         self.light = Texture.get_texture("churchlight")
#         self.pixel = Texture.get_texture("pixel")

#     def draw(self):
#         def ease(t):
#             t = min(max(0, t), 1)
#             return 3 * t * t - 2 * t * t * t
#         camera_pos = Vec(*main_cam.get_pos())
#         camera_center = camera_pos + view_size / 2

#         # for i in range(-10, 10):
#         #     ground_pos = parallax(Vec(*self.ground_size), Vec(self.ground_size[0] * i, 0 + self.ground_size[1]), 0)
#         #     EntityTools.draw_image(self.ground, Vec(0, ground_pos.y).unp(), (self.ground_size[0], self.ground_size[1]), program="floor", overhead_data=[sw.looping.GameLoop.view_width, sw.looping.GameLoop.view_height, self.ground_size[0] / cam_factor * i / sw.looping.GameLoop.view_width, .86, 0, 1, 3.5, 1, 2.3, 0, 0])
#         # # ground_pos = parallax(Vec(*self.ground_size), Vec(self.ground_size[0] * 0, 150 + self.ground_size[1]), 0)
#         # # EntityTools.draw_image_3d(self.ground, (-camera_pos.x, -10, -.1), (self.ground_size[0], self.ground_size[1], 1), (pi / 2, 0, 0), offset=(0, -300), color=(127, 127, 127), program="def3d")
#         # # for i in range(-10, 10):
#         # back_bg_pos = parallax(Vec(*self.back_bg_size), Vec(self.back_bg_size[0], 0), .333 * 1.36)
#         # EntityTools.draw_image(self.back_background, back_bg_pos.unp(), self.back_bg_size, color=(185, 161, 141))
#         # # EntityTools.draw_image_3d(self.back_background, (back_bg_pos.x - camera_pos.x, back_bg_pos.y, -2), (self.back_bg_size[0], self.back_bg_size[1], 1), (0, 0, 0), offset=(0, -300), color=(127, 127, 127), program="def3d")
#         # #     EntityTools.draw_image(self.back_background_glass, back_bg_pos.unp(), self.back_bg_size)
#         # for i in range(-10, 10):
#         #     light_pos = parallax(Vec(*self.back_bg_size), Vec(self.back_bg_size[0] * i, 0), .333 * 1.36)
#         #     alpha_val = 1.1 * max(0, ease((200 - abs(light_pos.x - camera_center.x)) / 200))
#         #     EntityTools.draw_image(self.back_background_light, light_pos.unp(), self.back_light_size, alpha=alpha_val, color=(255, 236, 175))

#         # for i in range(-10, 10):
#         #     front_bg_pos = parallax(Vec(*self.front_bg_size), Vec(self.front_bg_size[0] * i + 200, 0), 0.2)

#         #     EntityTools.draw_image(self.front_background, front_bg_pos.unp(), self.front_bg_size)

# class Foreground(Entity):
#     def __init__(self):
#         super().__init__((0, 0), order=6)
#         self.vignette = Texture.get_texture("vignette")
#         self.vignette_size = (self.vignette.get_width(), self.vignette.get_height())
#         self.front_pillar = Texture.get_texture("frontline")
#         self.pillar_size = (self.front_pillar.get_width() * 2, self.front_pillar.get_height() * 2)
#         self.sprite = Texture.get_texture("ground")
#         self.vignette_alpha = 0.6
#         self.spr_body = Texture.get_texture("PlayerBody")
#         self.k = 1

#     def draw(self):
#         camera_pos = Vec(*main_cam.get_pos())
#         camera_center = camera_pos + view_size / 2

#         EntityTools.draw_image_3d(self.sprite, (0, -200, -1), (1000, 1000, 1), (pi / 2, 0, 0))
#         EntityTools.draw_image_3d(self.sprite, (0, -200, -10), (1000, 1000, 1), (0, 0, 0))
    
#         # for i in range(-10, 10):
#         #     front_bg_pos = Vec(-camera_pos.x, 0) * 10 + Vec(1440 * i, 0)
#         #     EntityTools.draw_image(self.front_pillar, front_bg_pos.unp(), self.pillar_size)

#         # EntityTools.draw_image(self.vignette, camera_center.unp(), (view_size * 1.01).unp(), alpha=self.vignette_alpha)

#         # EntityTools.draw_image_3d(self.sprite, (0 - camera_pos.x - view_size.x / 2, -50, -.5), (1080, 1080, 1), (pi / 2, 0, 0), (0,  camera_pos.y), program="def3d")
#         # EntityTools.draw_image_3d(self.spr_body, (player.pos.x - camera_pos.x - view_size.x / 2, -player.pos.y - 40, -.5), (20, 20, 1), (0, 0, 0), (0,  camera_pos.y), program="def3d")
        
# player = Player((200, -100))
# background = Background()
# foreground = Foreground()
# Block((100, 50), (10000, 100))

# sw.start()