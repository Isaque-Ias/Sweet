import numpy as np
from math import cos, sin, pi
import sweet as sw
from random import random
from pygame.locals import *
import pygame as pg
from pathlib import Path
from sweet.linalg.vector import Vec
from sweet.inputting import Input
from OpenGL.GL import *
from PIL import Image
from sweet.graphics.texture import Imaging

sw.looping.GameLoop.set_screen_size((1300, 700))
sw.looping.GameLoop.set_resizable(True)
sw.looping.GameLoop.setup()

SOURCES = Path.cwd() / "app" / "sources"

sw.graphics.texture.Texture.set_texture("a", SOURCES / "gef.gif")

sw.graphics.texture.Texture.set_texture("arma", SOURCES / "arma.png")
sw.graphics.texture.Texture.set_texture("bala", SOURCES / "bala.png")

sw.graphics.texture.Texture.set_texture("pexe", SOURCES / "pexe.png")
sw.graphics.texture.Texture.set_texture("grama", SOURCES / "grass.png")
sw.graphics.texture.Texture.set_texture("ceu", SOURCES / "ceu.jpg")

a = sw.graphics.texture.Texture.get_texture("ceu")
a.upload()
b = sw.graphics.texture.Texture.get_texture("bala")
b.upload()
gif = sw.graphics.texture.Texture.get_texture("a")
gif.upload()
c = sw.graphics.texture.Texture.get_texture("pexe")
c.upload()

global cam
cam = sw.camera.Camera.get_main_camera()
cam.set_scale((1, 1))

class Ka(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), image = c, order = 1, tick=True)
        self.cam_scal = Vec(1, 1)

    def tick(self):
        screen_size = Vec(*sw.entity.EntityTools.get_screen_size())
        if sw.inputting.Input.get_press(K_w):
            self.pos.y -= 5
        if sw.inputting.Input.get_press(K_s):
            self.pos.y += 5
        if sw.inputting.Input.get_press(K_a):
            self.pos.x -= 5
        if sw.inputting.Input.get_press(K_d):
            self.pos.x += 5

        if sw.inputting.Input.get_press(K_o):
            self.cam_scal = self.cam_scal * 1.1
            cam.set_scale(self.cam_scal.unp())

        if sw.inputting.Input.get_press(K_p):
            self.cam_scal = self.cam_scal / 1.1
            cam.set_scale(self.cam_scal.unp())

        if sw.inputting.Input.get_press(K_k):
            cam.set_angle(cam.get_angle() + 5)

        if sw.inputting.Input.get_press(K_l):
            cam.set_angle(cam.get_angle() - 5)

        cam.set_pos((self.pos - screen_size * cam.get_scale()[0]/ 2).unp())

    def draw(self):
        for i in range(-10, 10):
            for j in range(-10, 10):
                col = (25 * i, 0, 0)
                sw.entity.EntityTools.draw_image(self.image, (self.pos + Vec(i * 10, j * 10)).unp(), (10, 10), self.pos.x / 10, color=col)
        sw.entity.EntityTools.draw_image(self.image, (self.pos).unp(), (10, 10), self.pos.x / 10, static=True)

class Ceu(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), image = a, order=0, tick=True)
        self.gif = sw.graphics.texture.Texture.get_texture("a")
        self.time = 0

    def tick(self):
        self.time += 1
        if self.time > 0 and self.gif._current_frame < 190:
            self.gif.next_frame()
            self.time = 0

    def draw(self):
        screen_size = Vec(*sw.entity.EntityTools.get_screen_size())
        sw.entity.EntityTools.draw_image(self.image, (screen_size/2).unp(), screen_size.unp())

        sw.entity.EntityTools.draw_image(self.gif, (screen_size/2).unp(), (screen_size / 2).unp())

Ceu()
Ka()
sw.start()

# curr_img = sw.graphics.texture.Texture.get_texture("grama")
"""canva_img = curr_img.resize_canvas(curr_img.get_image(), curr_img.width * 100, curr_img.height) 
for i in range(100):
    canva_img = canva_img.paste_image(canva_img.get_image(), curr_img.get_image(), 97 * (i + 1), 0)
canva_img.set_occupation("grass_line")
canva_img.convert(sw.common.FileType.SHADERATLAS)

sw.graphics.texture.Texture.set_texture("ceu", SOURCES / "ceu.jpg", sw.common.FileType.SHADERATLAS)

class UI(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), sw.graphics.texture.Texture.get_texture("ceu"), order=1)

    def draw(self):
        screen_size = Vec(*sw.entity.EntityTools.get_screen_size())
        cam_pos = Vec(*sw.camera.Camera.get_main_camera().get_pos())
        sw.entity.EntityTools.draw_image(self.image, (cam_pos + screen_size / 2).unp(), screen_size.unp(), 0)

class Bullet(sw.entity.Entity):
    def __init__(self, pos: tuple, vel: Vec) -> None:
        super().__init__(pos, sw.graphics.texture.Texture.get_texture("bala"), layer=0, order=2, tick=True)
        self.vel = vel

    def tick(self):
        self.pos += self.vel / 60

    def draw(self):
        sw.entity.EntityTools.draw_image(self.image, (self.pos).unp(), (10, 10 * self.image.height / self.image.width), self.vel.angle() + 90)

class Peixe(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), sw.graphics.texture.Texture.get_texture("pexe"), layer=0, order=2, tick=True)
        self.image.convert(sw.common.FileType.SHADERATLAS)
        self.arma = sw.graphics.texture.Texture.get_texture("arma")
        self.vel = Vec(0, 0)
        self.speed = 2
        self.size = 100
        self.cam = sw.camera.Camera.get_main_camera()
        self.animation_time = 0
        self.walk_transform = 0
        self.animation_type = "idle"
        self.show_go = Vec(0, 0)
        self.show_angle = 0
        self.jump_dir = 1
        self.sign = 0
        self.gun_angle = 0

    def tick(self):
        screen_size = Vec(*sw.entity.EntityTools.get_screen_size())
        pos = Vec(*self.cam.get_pos())
        goal = self.pos - screen_size / 2
        pos += (goal - pos) / 5
        self.cam.set_pos(pos.unp())
        self.pos += self.vel
        self.vel.x *= 0.7
        self.vel.y += .8
        
        self.sign = -1 if np.sign(self.vel.x) == 0 else np.sign(self.vel.x)

        if self.pos.y > 0:
            self.animation_type = "idle"
            self.pos.y = 0
            self.vel.y = min(0, self.vel.y)

        if Input.get_press(K_a):
            self.vel.x -= self.speed 
        if Input.get_press(K_d):
            self.vel.x += self.speed 

        if Input.get_press(K_d) or Input.get_press(K_a):
            self.walk_transform = min(10, self.walk_transform + .75)
            if self.pos.y >= 0:
                self.animation_time += 1
                self.animation_type = "walk"
        else:
            self.walk_transform = max(0, self.walk_transform - .75)
        
        if Input.get_press(K_SPACE) and self.pos.y >= 0:
            self.animation_time = 0
            self.animation_type = "jump"
            self.jump_dir = self.sign
            
            self.vel.y = -18

        if Input.mouse_pressed(BUTTON_LEFT):
            pos = (self.show_go + Vec(20 * self.sign, 10).rotate(self.gun_angle)).unp()
            extra = 180 * (-self.sign / 2 + 0.5)
            vel = Vec(cos((self.gun_angle + extra) * pi / 180), sin((self.gun_angle + extra) * pi / 180)) * 3000
            Bullet(pos, vel)

    def angle_add(self, curr, goal, fac=3):
        diff = ((goal % 360) - curr + 180) % 360 - 180
        curr += diff / fac
        curr = curr % 360
        return curr

    def draw(self):
        if self.animation_type == "idle":
            self.show_go += (self.pos - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, 0)
        if self.animation_type == "jump":
            self.show_go += (self.pos - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, self.sign * self.animation_time * 8.6)
            self.animation_time += 1
        if self.animation_type == "walk":
            loop = 20
            animation = Vec(cos(self.sign * self.animation_time * pi / loop) * loop, 0.25 * (self.animation_time % loop) * (self.animation_time % loop - loop))
            animation_angle = 40 * cos(self.animation_time * pi / loop)
            self.show_go += ((self.pos + animation) - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, animation_angle)

        self.gun_angle = self.angle_add(self.gun_angle, self.show_angle, 10)

        sw.entity.EntityTools.draw_image(self.image, (self.show_go).unp(), (-150 * self.sign, 150 * self.image.height / self.image.width), self.show_angle)
        sw.entity.EntityTools.draw_image(self.arma, (self.show_go + Vec(20 * self.sign, 10).rotate(self.gun_angle)).unp(), (-200 * self.sign, 200 * self.arma.height / self.arma.width), self.gun_angle)

class Grass(sw.entity.Entity):
    def __init__(self, pos, size, layer="c"):
        l = size
        if not layer=="c":
            l = layer
        super().__init__(pos, sw.graphics.texture.Texture.get_texture("grass_line"), layer=l, order=2)
        self.size = size

    def draw(self):
        sw.entity.EntityTools.draw_image(self.image, (self.pos + Vec(self.pos.x - peixe.pos.x, 0) * (self.size - 1)).unp(), (10000 * self.size, 10000 * self.size * self.image.height / self.image.width), 0)

UI()
peixe = Peixe()

Grass((0, 50), 1)
Grass((0, 50 * 2), 1.5)
Grass((0, 50 * 2 ** 2), 2.25)
Grass((0, 50 * 2 ** 3), 2.25 * 1.5)
Grass((0, 50 / 2), 1 / 1.5, -1)

sw.start()"""