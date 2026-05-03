from .graphics.shaders import ShaderHandler
from .graphics.texture import Texture, Imaging, Video
from .camera import Camera, Cam
from OpenGL.GL import *
import pygame as pg
from .common import TextureData
from typing import Sequence
from .linalg.vector import Vec
import numpy as np
from PIL import Image
from dataclasses import dataclass

@dataclass
class Sprite:
    pos: tuple
    scale: tuple
    layer: int
    rotation: float
    uv: tuple
    tex_id: int
    static: bool
    program: bool
    unit: int
    overhead: list

class EntityTools:
    ShaderHandler.add_shader_file("def", layout = {
        "vao": [("iPos", 2),
        ("iScale", 2),
        ("iRot", 2),
        ("iUVOff", 2),
        ("iUVScale", 2),
        ("iRgb", 3),
        ("iAlpha", 1)]
    })
    _font: pg.font = None
    _z = 0

    @staticmethod
    def get_default_shader_layout():
        return {"vao": [("iPos", 2),
        ("iScale", 2),
        ("iRot", 2),
        ("iUVOff", 2),
        ("iUVScale", 2),
        ("iRgb", 3),
        ("iAlpha", 1)]
    }

    @staticmethod
    def get_cam(cam: str) -> Cam:
        return Camera.get_camera(cam)

    @classmethod
    def get_default_shaders(cls) -> dict[str, str]:
        return ShaderHandler.get_shader_program("def")

    @staticmethod
    def get_screen_size() -> tuple:
        return ShaderHandler.get_size()

    @staticmethod
    def tex(tex) -> TextureData:
        return Texture.get_texture(tex)

    @staticmethod
    def default_mvp(entity) -> np.array:
        return ShaderHandler.affine_transform((entity.x, entity.y), (entity.width, entity.height), entity.angle, True)

    @staticmethod
    def default_draw(entity) -> None:
        ShaderHandler.render(entity.get_mvp(), Texture.get_texture(entity.image))

    @classmethod
    def draw_image(cls,
                   image: Imaging | Video,
                   pos: tuple,
                   scale: tuple,
                   angle: float=0,
                   color: tuple=(255, 255, 255),
                   alpha: float=1,
                   static: bool=False,
                   program: str=None,
                   unit=GL_TEXTURE0) -> None:

        color = (color[0] / 255, color[1] / 255, color[2] / 255)
        sprite = Sprite(pos, scale, cls._z, angle, image.uv.uv, image.get_tex_id(), static, program, unit, [*color, alpha])
        cls._z += 1
        ShaderHandler.render_add(sprite)

    @classmethod
    def set_font(cls, font: pg.font) -> None:
        cls._font = font

    @classmethod
    def get_font(cls) -> pg.font:
        return cls._font

    @classmethod
    def draw_text(cls,
                  image: Imaging,
                  text: str,
                  pos: tuple,
                  scale: tuple,
                  angle: float=0,
                  color: tuple=(255, 255, 255),
                  alpha: float=1,
                  static: bool=True,
                  align: tuple=(0, 0),
                  program: str=None,
                   unit=GL_TEXTURE0) -> None:
        font_surf: pg.Surface = cls.get_font().render(text, True, (255, 255, 255))
        width: int
        height: int

        data = pg.image.tostring(font_surf, "RGBA", True)
        size = font_surf.get_size()
        new_image = Image.frombytes("RGBA", size, data)
        image.set_image(new_image)
        image.upload()

        width, height = (image.width, image.height)
        cls.draw_image(image,
                       (pos[0] + width * scale[0] * align[0] / 2, pos[1] + height * scale[1] * align[1] / 2),
                       (width * scale[0], height * scale[1]),
                       angle=angle,
                       color=color,
                       alpha=alpha,
                       static=static,
                       program=program,
                       unit=unit)

class Entity:
    def __init__(self,
                 pos: tuple,
                 image: Imaging=None,
                 scale: tuple=(0, 0),
                 angle: int=0,
                 layer: int=0,
                 order: int=-1,
                 pre_tick: bool=False,
                 tick: bool=False,
                 pos_tick: bool=False) -> None:
        self.pos = Vec(*pos)
        self.image = image
        self.scale = Vec(*scale)
        self.angle = angle
        self.layer = int(layer)
        self.order = order
        self.mask = Mask()
        EntityManager.agend_entity(self, order, pre_tick, tick, pos_tick)
            
    def set_layer(self, layer: int) -> None:
        layer = int(layer)
        if not self.layer == layer:
            EntityManager.agend_layer_change(self, layer)
        
    def set_order(self, order: int) -> None:
        order = int(order)
        if not self.order == order:
            EntityManager.agend_order_change(self, order)

    def tick(self) -> None:
        pass

    def pre_draw(self) -> None:
        pass

    def draw(self) -> None:
        pass
    
    def draw_gui(self) -> None:
        pass

    def get_mvp(self) -> None:
        pass
    
    def set_id(self, id: int) -> None:
        self._id = id

    def get_id(self) -> int:
        return self._id
    
    def __str__(self) -> str:
        return f"{type(self).__name__} - {self._id}"
    
    def destroy_self(self):
        EntityManager.agend_destroy(self)

class EntityManager:
    _entities: dict[dict[Entity]] = {}
    _content_orders: list[int] = []
    _content_layers: dict[list[int]] = {}
    _instance_groups = {}

    _pre_tick: dict[Entity] = {}
    _tick: dict[Entity] = {}
    _pos_tick: dict[Entity] = {}

    _layer_changes: dict[Entity, int] = {}
    _order_changes: dict[Entity, int] = {}
    _entity_changes: dict[Entity] = {}
    _destroy_changes: dict[Entity] = {}
    _ticks: dict[list[Entity]] = {}
    _id: int = 0

    @classmethod
    def add_instance(cls, instance: object) -> None:
        name = instance.__class__

        if cls._instance_groups.get(name) == None:
            cls._instance_groups[name] = {}

        cls._instance_groups[name][instance._id] = instance

    @classmethod
    def remove_instance(cls, instance: object) -> None:
        name = instance.__class__
        if not cls._instance_groups.get(name) == None:
            if not cls._instance_groups[name].get(instance._id) == None:
                del cls._instance_groups[name][instance._id]
                if len(cls._instance_groups[name]) == 0:
                    del cls._instance_groups[name]

    @classmethod
    def get_entity_group(cls, group) -> list:
        return list(map(lambda x: x[1], cls._instance_groups[group].items()))

    @staticmethod
    def find_insert_index(arr: list[int], target: int) -> int:
        left, right = 0, len(arr) - 1

        while left <= right:
            mid = (left + right) // 2

            if arr[mid] == target:
                return -1
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1

        return left

    @classmethod
    def get_layer_changes(cls) -> dict[Entity, int]:
        return cls._layer_changes

    @classmethod
    def get_order_changes(cls) -> dict[Entity, int]:
        return cls._order_changes

    @classmethod
    def get_entity_changes(cls) -> dict[Entity, int]:
        return cls._entity_changes

    @classmethod
    def get_destroy_changes(cls) -> dict[Entity]:
        return cls._destroy_changes

    @classmethod
    def set_layer_change(cls, entity: Entity, layer: int) -> None:
        if hasattr(entity, "_id"):
            cls.remove_entity_layer(entity)
        entity.layer = layer
        cls.add_entity_layer(entity)

    @classmethod
    def set_order_change(cls, entity: Entity, order: int) -> None:
        if hasattr(entity, "_id"):
            cls.remove_entity_order(entity)
        entity.order = order
        cls.add_entity_order(entity)

    @classmethod
    def agend_layer_change(cls, entity: Entity, layer: int) -> None:
        cls._layer_changes[entity._id] = [entity, layer]

    @classmethod
    def agend_order_change(cls, entity: Entity, order: int) -> None:
        cls._order_changes[entity._id] = [entity, order]

    @classmethod
    def agend_entity(cls, entity, order, pre_tick, tick, pos_tick):
        cls._entity_changes[entity] = [entity, order, pre_tick, tick, pos_tick]

    @classmethod
    def agend_destroy(cls, entity):
        cls._destroy_changes[entity] = entity

    @classmethod
    def clear_agend(cls):
        cls._entity_changes = {}
        cls._order_changes = {}
        cls._layer_changes = {}
        cls._destroy_changes = {}

    @classmethod
    def create_entity(cls, entity: Entity, order: int, pre_tick: bool, tick: bool, pos_tick: bool) -> None:
        entity.set_id(cls._id)
        cls._id += 1
        EntityManager.add_instance(entity)

        if not order == -1:
            cls.add_entity_layer(entity)
        
        if pre_tick:
            cls.add_entity_tick(entity, 0)
        if tick:
            cls.add_entity_tick(entity, 1)
        if pos_tick:
            cls.add_entity_tick(entity, 2)

    @classmethod
    def destroy_entity(cls, entity: Entity) -> None:
        cls.remove_entity_tick(entity, 0)
        cls.remove_entity_tick(entity, 2)
        cls.remove_entity_tick(entity, 3)
        cls.remove_entity_layer(entity)
        cls.remove_instance(entity)

    @classmethod
    def add_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0:
            cls._pre_tick[entity._id] = entity
        elif tick_type == 1:
            cls._tick[entity._id] = entity
        elif tick_type == 2:
            cls._pos_tick[entity._id] = entity

    @classmethod
    def remove_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0 and not cls.__pre_tick.get(entity._id) is None:
            cls._pre_tick.remove(entity._id)
        elif tick_type == 1 and not cls.__tick.get(entity._id) is None:
            cls._tick.remove(entity._id)
        elif tick_type == 2 and not cls.__pos_tick.get(entity._id) is None:
            cls._pos_tick.remove(entity._id)

    @classmethod
    def add_entity_layer(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if cls._entities.get(order) == None:
            cls._entities[order] = {layer: [entity]}
        else:
            if cls._entities[order].get(layer) == None:
                cls._entities[order][layer] = []
            cls._entities[order][layer].append(entity)
        
        index = cls.find_insert_index(cls._content_orders, order)
        if not index == -1:
            cls._content_orders.insert(index, order)

        if cls._content_layers.get(order) == None:
            cls._content_layers[order] = [layer]
        else:
            index = cls.find_insert_index(cls._content_layers[order], layer)
            if not index == -1:
                cls._content_layers[order].insert(index, layer)

    @classmethod
    def remove_entity_layer(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if order not in cls._entities:
            return
        if layer not in cls._entities[order]:
            return

        layer_list: list[Entity] = cls._entities[order][layer]
        layer_list.remove(entity)

        if not layer_list:
            cls._content_layers[order].remove(layer)
            del cls._entities[order][layer]

            if not cls._content_layers[order]:
                cls._content_layers.pop(order)
                cls._content_orders.remove(order)

                del cls._entities[order]

    @classmethod
    def remove_entity_order(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if not cls._entities.get(order) == None:
            if not cls._entities[order].get(layer) == None:
                del cls._entities[order][layer]
                if len(cls._entities[order][layer]) == 0:
                    del cls._entities[order][layer]
                if len(cls._entities[order]) == 0:
                    del cls._entities[order]
                    cls._content_orders.remove(order)

    @classmethod
    def get_all_entities(cls) -> dict[dict[Entity]]:
        return cls._entities

    @classmethod
    def get_tick_entities(cls, tick_type: int) -> dict[Entity]:
        if tick_type == 0:
            return cls._pre_tick
        elif tick_type == 1:
            return cls._tick
        elif tick_type == 2:
            return cls._pos_tick

    @classmethod
    def get_content_orders(cls) -> list[int]:
        return cls._content_orders

    @classmethod
    def get_content_layers(cls, order: int) -> list[int]:
        return cls._content_layers[order]
    
class Polygon:
    def __init__(self, vertices: Sequence[Vec]) -> None:
        self.vertices = vertices

    def rotate(self, angle: float) -> "Polygon":
        vertices = [vertex.rotate(angle) for vertex in self.vertices]
        return Polygon(vertices)

    def translate(self, pos: Vec) -> "Polygon":
        vertices = [vertex + pos for vertex in self.vertices]
        return Polygon(vertices)

    def scale(self, multiplier: Vec) -> "Polygon":
        vertices = [Vec(vertex.x * multiplier.x, vertex.y * multiplier.y) for vertex in self.vertices]
        return Polygon(vertices)

class Mask:
    def __init__(self):
        self.polygons = {}

    def add_polygon(self, name: str, polygon: Polygon) -> None:
        self.polygons[name] = polygon

    def get_polygon(self, name) -> Polygon:
        return self.polygons[name]
    
    def def_polygon(self) -> Polygon:
        first = list(self.polygons.keys())[0]
        return self.polygons[first]