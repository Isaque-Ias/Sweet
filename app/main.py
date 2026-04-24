import sweet as sw
from sweet.graphics.texture import Texture
from sweet.entity import EntityTools, Entity
from sweet.inputting import Input
from pathlib import Path
from sweet.linalg.vector import Vec
from pygame.locals import *
from math import cos, radians

SOURCE = Path.cwd() / "app" / "sources"
sw.looping.GameLoop.set_title("Assobi")
height, width = sw.looping.GameLoop.view_width, sw.looping.GameLoop.view_height
sw.looping.GameLoop.set_screen_size((height, width))

sw.init()

Texture.set_texture("Pixel", SOURCE / "build" / "pixel.png")
Texture.get_texture("Pixel").upload()
Texture.set_texture("icon", SOURCE / "ceu.jpg")
icon = Texture.get_texture("icon")
sw.looping.GameLoop.set_icon(icon.get_image())

def sign(x):
    return (x > 0) - (x < 0)

class Plant(Entity):
    def __init__(self, pos):
        super().__init__(pos, order=5, tick=True)
        self.vertices = [0, 0, 10, 0, 0, 0, 10, 20, 0, 0, 0, 0, 20, 20, 20, 20, 20, 100]
        self.image = Texture.get_texture("Pixel")
        self.length = 200
        self.thickness = 10
        self.time = 0
        self.torsion = 50
        self.mode = "idle"
        self.pose = [(1, 180)]

    def tick(self):
        if self.mode == "idle":
            self.time += 1
            self.vertices[0] = cos(radians(self.time * 4)) * 50
            for i in range(1, len(self.vertices)):
                self.vertices[i] += (self.vertices[i - 1] - self.vertices[i]) / 5

        if self.mode == "pose":
            current_pose = 0
            old_pos = Vec(0, 0)
            total_vertices = len(self.vertices)
            for i in range(len(self.vertices)):
                angle = self.vertices[i] - 90
                new_pos = old_pos + Vec((self.length / (total_vertices - 1)), 0).rotate(angle)

                percentage = i / len(self.vertices)
                if percentage > self.pose[current_pose][0] and current_pose < len(self.pose):
                    current_pose += 1

                goal_pos = Vec(self.pose[current_pose][0] * self.length, 0).rotate(self.pose[current_pose][1])
                perfect_angle = -(goal_pos - new_pos).angle()
                print(goal_pos, i, new_pos, perfect_angle)
                self.vertices[i] += (perfect_angle - self.vertices[i]) / 10

                old_pos = new_pos

        for i in range(len(self.vertices)):
            if abs(self.vertices[i]) > self.torsion:
                self.vertices[i] -= sign(self.vertices[i]) * (abs(self.vertices[i]) - self.torsion) / 3

    def draw(self):
        old_pos = self.pos
        total_vertices = len(self.vertices)
        for i in range(total_vertices):
            angle = self.vertices[i] - 90
            new_pos = old_pos + Vec((self.length / (total_vertices - 1)), 0).rotate(angle)

            difference = (old_pos - new_pos)
            distance = difference.magnitude()
            EntityTools.draw_image(self.image, (new_pos / 2 + old_pos / 2).unp(), (distance + self.thickness, self.thickness), angle)
            
            old_pos = new_pos

screen_size = Vec(*EntityTools.get_screen_size())
Plant((screen_size / 2).unp())

sw.start()