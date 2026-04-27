import sweet as sw
from sweet.entity import *
from sweet.inputting import *
from sweet.graphics.texture import *
from pathlib import Path
from pygame.locals import *

SOURCE = Path.cwd() / "app" / "sources"
sw.looping.GameLoop.set_screen_size((sw.looping.GameLoop.view_width, sw.looping.GameLoop.view_height))
sw.init()

Texture.set_texture("PlayerBody", SOURCE / "player_body.png").upload()
Texture.set_texture("PlayerLeg", SOURCE / "player_leg.png").upload()

class Player(Entity):
    def __init__(self, pos):
        super().__init__(pos, order=5, tick=True)
        self.spr_body = Texture.get_texture("PlayerBody")
        self.spr_legs = Texture.get_texture("PlayerLeg")
        self.size = 0.2
        self.left_leg_angle = [0, 25]
        self.right_leg_angle = [0, -25]

    def tick(self):
        self.left_leg_angle[0] = (Vec(*pg.mouse.get_pos()) - self.pos).angle() + 90

    def draw(self):
        body_width, body_height = self.spr_body.get_width() * self.size, self.spr_body.get_height() * self.size
        leg_width, leg_height = self.spr_legs.get_width() * self.size, self.spr_legs.get_height() * self.size
        
        left_leg_center = Vec(.3 * body_width, .0 * body_height) + Vec(0, leg_height / 2).rotate(self.left_leg_angle[0])
        right_leg_center = Vec(-.3 * body_width, .0 * body_height) + Vec(0, leg_height / 2).rotate(self.right_leg_angle[0])
        
        bottom_left_leg_center = Vec(.3 * body_width, .0 * body_height) + Vec(0, leg_height - leg_width / 2).rotate(self.left_leg_angle[0]) + Vec(0, leg_height / 2).rotate(self.left_leg_angle[1])
        bottom_right_leg_center = Vec(-.3 * body_width, .0 * body_height) + Vec(0, leg_height - leg_width / 2).rotate(self.right_leg_angle[0]) + Vec(0, leg_height / 2).rotate(self.right_leg_angle[1])
        
        EntityTools.draw_image(self.spr_legs, (self.pos + left_leg_center).unp(), (leg_width, leg_height), self.left_leg_angle[0])
        EntityTools.draw_image(self.spr_legs, (self.pos + bottom_left_leg_center).unp(), (leg_width, leg_height), self.left_leg_angle[1])
        
        EntityTools.draw_image(self.spr_body, self.pos.unp(), (body_width, body_height))

        EntityTools.draw_image(self.spr_legs, (self.pos + right_leg_center).unp(), (leg_width, leg_height), self.right_leg_angle[0])
        EntityTools.draw_image(self.spr_legs, (self.pos + bottom_right_leg_center).unp(), (leg_width, leg_height), self.right_leg_angle[1])

Player((200, 200))

sw.start()