import numpy as np
from math import cos, sin, pi
import sweet as sw
from random import random
from pygame.locals import *
import pygame as pg
from pathlib import Path
from sweet.linalg.vector import Vec
from sweet.inputting import Input

sw.looping.GameLoop.set_screen_size((1300, 700))
sw.looping.GameLoop.set_resizable(True)
sw.looping.GameLoop.setup()

SOURCES = Path.cwd() / "app" / "sources"

sw.graphics.texture.Texture.set_texture("pexe", SOURCES / "pexe.png", sw.common.FileType.PILIMAGE)
sw.graphics.texture.Texture.set_texture("grama", SOURCES / "grass.png", sw.common.FileType.PILIMAGE)
curr_img = sw.graphics.texture.Texture.get_texture("grama")
canva_img = curr_img.resize_canvas(curr_img.get_image(), curr_img.width * 20, curr_img.height) 
curr_img.set_image(canva_img, sw.common.FileType.PILIMAGE)
for i in range(20):
    image = curr_img.paste_image(curr_img.get_image(), curr_img.get_image(), 97 * (i + 1), 0)
    curr_img.set_image(image, sw.common.FileType.PILIMAGE)
curr_img.convert(sw.common.FileType.SHADERATLAS)
sw.graphics.texture.Texture.set_texture("ceu", SOURCES / "ceu.jpg", sw.common.FileType.PILIMAGE)

class UI(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), sw.graphics.texture.Texture.get_texture("ceu"), order=1)
        self.image.convert(sw.common.FileType.SHADERATLAS)

    def draw(self):
        screen_size = Vec(*sw.entity.EntityTools.get_screen_size())
        cam_pos = Vec(*sw.camera.Camera.get_main_camera().get_pos())
        sw.entity.EntityTools.draw_image(self.image, (cam_pos + screen_size / 2).unp(), screen_size.unp(), 0)

class Peixe(sw.entity.Entity):
    def __init__(self):
        super().__init__((0, 0), sw.graphics.texture.Texture.get_texture("pexe"), layer=0, order=2, tick=True)
        self.image.convert(sw.common.FileType.SHADERATLAS)
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
            
            self.vel.y = -12

    def angle_add(self, curr, goal):
        diff = ((goal % 360) - curr + 180) % 360 - 180
        curr += diff / 3
        curr = curr % 360
        return curr

    def draw(self):
        if self.animation_type == "idle":
            self.show_go += (self.pos - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, 0)
        if self.animation_type == "jump":
            self.show_go += (self.pos - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, self.sign * self.animation_time * 12)
            self.animation_time += 1
        if self.animation_type == "walk":
            loop = 20
            animation = Vec(cos(self.sign * self.animation_time * pi / loop) * loop, 0.25 * (self.animation_time % loop) * (self.animation_time % loop - loop))
            animation_angle = 40 * cos(self.animation_time * pi / loop)
            self.show_go += ((self.pos + animation) - self.show_go) / 3
            self.show_angle = self.angle_add(self.show_angle, animation_angle)
        
        sw.entity.EntityTools.draw_image(self.image, (self.show_go).unp(), (-150 * self.sign, 150 * self.image.height / self.image.width), self.show_angle)

class Grass(sw.entity.Entity):
    def __init__(self, pos, size):
        super().__init__(pos, sw.graphics.texture.Texture.get_texture("grama"), layer=size, order=2)
        self.size = size

    def draw(self):
        sw.entity.EntityTools.draw_image(self.image, (self.pos + Vec(self.pos.x - peixe.pos.x, 0) * self.size).unp(), (2000 * self.size, 2000 * self.size * self.image.height / self.image.width), 0)

UI()
peixe = Peixe()

Grass((0, 50), 1)
Grass((0, 50 * 2), 1.5)
Grass((0, 50 * 2 ** 2), 2.25)
Grass((0, 50 * 2 ** 3), 2.25 * 1.5)

sw.start()