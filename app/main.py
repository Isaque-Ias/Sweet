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
Texture.set_texture("pixel", SOURCE / "build" / "pixel.png").upload()

grv = 10 / 60

class Player(Entity):
    def __init__(self, pos):
        super().__init__(pos, order=5, tick=True)
        self.spr_body = Texture.get_texture("PlayerBody")
        self.spr_legs = Texture.get_texture("PlayerLeg")
        self.size = 0.2
        self.scale = Vec(self.spr_body.get_width() * self.size, self.spr_body.get_height() * self.size)
        
        vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]

        self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))

        self.jump_power = 5
        self.speed = 3
        self.velocity = Vec(0, 0)

    def tick(self):
        self.pos += self.velocity
        self.velocity.y += grv

        if Input.get_press(K_a):
            self.pos.x -= 5
        if Input.get_press(K_d):
            self.pos.x += 5
        if Input.get_press(K_SPACE):
            self.velocity.y = -self.jump_power
            
        def response(entity, other, data):
            entity.pos += data.mtv * (data.is_b * 2 - 1)

        sw.linalg.collision.Collision.collision_list(self, Block, apply_func=response)

    def draw(self):
        EntityTools.draw_image(self.spr_body, self.pos.unp(), self.scale.unp())

class Block(Entity):
    def __init__(self, pos, size=(100, 100), angle=0):
        super().__init__(pos, Texture.get_texture("pixel"), size, angle, order=5)
        vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]
        self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))

    def draw(self):
        EntityTools.draw_image(self.image, self.pos.unp(), self.scale.unp(), self.angle, color=(127, 127, 127))

a = Player((200, 200))
Block((100, 400))
Block((200, 400))

sw.start()