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

grv = 30 / 60

class Player(Entity):
    def __init__(self, pos):
        super().__init__(pos, order=5, tick=True)
        self.spr_body = Texture.get_texture("PlayerBody")
        self.spr_legs = Texture.get_texture("PlayerLeg")
        self.size = 0.2
        self.scale = Vec(self.spr_body.get_width() * self.size, self.spr_body.get_height() * self.size)
        
        vertices = [Vec(self.scale.x / 2, 0).rotate(angle * 360 / 15) for angle in range(15)]#self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]

        self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))

        self.jump_power = 10
        self.speed = 120 / 60
        self.velocity = Vec(0, 0)
        self.floor_collision = False
        self.right_grip = False
        self.left_grip = False

        self.jumped = False

    def tick(self):
        self.velocity.y += grv
        self.velocity.x *= 0.8

        self.pos += self.velocity

        if Input.get_press(K_a):
            self.velocity.x -= self.speed
        if Input.get_press(K_d):
            self.velocity.x += self.speed

        if Input.get_press(K_SPACE) and not self.jumped:
            if self.floor_collision:
                self.velocity.y = -self.jump_power
                self.jumped = True
            elif self.left_grip:
                self.velocity.y = -self.jump_power
                self.velocity.x = 15
                self.jumped = True
            elif self.right_grip:
                self.velocity.y = -self.jump_power
                self.velocity.x = -15
                self.jumped = True

        if Input.get_released(K_SPACE):
            self.jumped = False
            
        self.floor_collision = False
        self.right_grip = False
        self.left_grip = False
        def response(entity, other, data):
            entity.pos += data.mtv * (data.is_b * 2 - 1)
            parallel = Vec(data.mtv.y, -data.mtv.x)
            parallel_magnitude = parallel.magnitude_squared()
            if parallel.cross(entity.velocity) > 0:
                entity.velocity = parallel * parallel.dot(entity.velocity) / parallel_magnitude

            if data.mtv.x == 0:
                if data.mtv.y > 0:
                    self.floor_collision = True
            else:
                if abs(data.mtv.y / data.mtv.x) > 1 and data.mtv.y > 0:
                    self.floor_collision = True

            if data.mtv.y == 0:
                if data.mtv.x > 0:
                    self.right_grip = True
                else:
                    self.left_grip = True

                self.velocity.y *= 0.7

        def response2(entity, other, data):
            entity.pos += data.mtv * (data.is_b * 2 - 1)
            other.pos -= data.mtv * (data.is_b * 2 - 1) / 2
            parallel = Vec(data.mtv.y, -data.mtv.x)
            parallel_magnitude = parallel.magnitude_squared()
            if parallel.cross(entity.velocity) > 0:
                entity.velocity = parallel * parallel.dot(entity.velocity) / parallel_magnitude

        sw.linalg.collision.Collision.collision_list(self, Block, apply_func=response)
        sw.linalg.collision.Collision.collision_list(self, Block2, apply_func=response)
        sw.linalg.collision.Collision.collision_list(self, Block3, apply_func=response2)

    def draw(self):
        EntityTools.draw_image(self.spr_body, self.pos.unp(), self.scale.unp())

class Block(Entity):
    def __init__(self, pos, size=(100, 100), angle=0):
        super().__init__(pos, image=Texture.get_texture("pixel"), scale=size, angle=angle, order=5)
        vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]
        self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))
        self.mask.polygons["main"] = self.mask.get_polygon("main").rotate(self.angle)

    def draw(self):
        EntityTools.draw_image(self.image, self.pos.unp(), self.scale.unp(), self.angle, color=(127, 127, 127))

class Block3(Entity):
    def __init__(self, pos, size=(100, 100), angle=0):
        super().__init__(pos, image=Texture.get_texture("pixel"), scale=size, angle=angle, order=5, tick=True)
        vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]
        self.mask.add_polygon("main", sw.linalg.collision.Polygon(vertices))
        self.mask.polygons["main"] = self.mask.get_polygon("main").rotate(self.angle)
        self.velocity = Vec(0, 0)

    def tick(self):
        
        self.velocity.y += grv
        self.velocity.x *= 0.8

        self.pos += self.velocity
        # print(self.velocity)

        def response2(entity, other, data):
            entity.pos += data.mtv * (data.is_b * 2 - 1)
            parallel = Vec(data.mtv.y, -data.mtv.x)
            parallel_magnitude = parallel.magnitude_squared()
            if parallel.cross(entity.velocity) > 0:
                entity.velocity = parallel * parallel.dot(entity.velocity) / parallel_magnitude

        sw.linalg.collision.Collision.collision_list(self, Block, apply_func=response2)

    def draw(self):
        EntityTools.draw_image(self.image, self.pos.unp(), self.scale.unp(), self.angle, color=(127, 127, 127))

class Block2(Entity):
    def __init__(self, pos, size=(100, 100), angle=0):
        super().__init__(pos, image=Texture.get_texture("pixel"), scale=size, angle=angle, order=5, tick=True)
        vertices = [self.scale / 2, self.scale.mirror_x() / 2, -self.scale / 2, self.scale.mirror_y() / 2]
        self.default_shape = sw.linalg.collision.Polygon(vertices)
        self.mask.add_polygon("main", self.default_shape)
        self.mask.polygons["main"] = self.default_shape.rotate(self.angle)
        
    def tick(self):
        self.angle += 1
        self.mask.polygons["main"] = self.default_shape.rotate(self.angle)

        def response2(entity, other, data):
            entity.pos += data.mtv * (data.is_b * 2 - 1)

        sw.linalg.collision.Collision.collision_list(self, Block, apply_func=response2)
        
    def draw(self):
        EntityTools.draw_image(self.image, self.pos.unp(), self.scale.unp(), self.angle, color=(127, 127, 127))

a = Player((200, 200))
Block((100, 400))
Block((200, 400))
Block((200, 650), (20000, 200))
Block2((1000, 450), (200, 200), 20)
Block3((100, 300))

sw.start()