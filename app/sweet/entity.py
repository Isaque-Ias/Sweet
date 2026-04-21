from .graphics.shaders import ShaderHandler
from .graphics.texture import Texture, Imaging
from .camera import Camera, Cam
from OpenGL.GL import *
import pygame as pg
from .common import TextureData, FileType
from .linalg.vector import Vec
import numpy as np
from math import pi
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
    unit: int

class EntityTools:
    ShaderHandler.add_shader_file("def")
    _font: pg.font = None
    _z = 0

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
                   image: Imaging,
                   pos: tuple,
                   scale: tuple,
                   angle: float=0,
                   color: tuple=(255, 255, 255),
                   alpha: float=1,
                   static: bool=False,
                   program: str=None,
                   unit=GL_TEXTURE0) -> None:
        if not program == None:
            ShaderHandler.set_shader(program)

        ShaderHandler.set_uniform_value("u_color", "4f", *map(lambda x: x / 255, color), alpha)
        sprite = Sprite(pos, scale, cls._z, angle, image.uv.uv, image.get_tex_id(), static, unit)
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
                  text: str,
                  pos: tuple,
                  image: Imaging,
                  scale: tuple,
                  color: tuple=(255, 255, 255),
                  alpha: float=1,
                  static: bool=True,
                  align: tuple=(0, 0)) -> TextureData:
        font_surf: pg.Surface = cls.get_font().render(text, True, (255, 255, 255))
        width: int
        height: int

        data = pg.image.tostring(font_surf, "RGBA", True)
        size = font_surf.get_size()
        ShaderHandler.replace_texture(ShaderHandler.get_image(), Image.frombytes("RGBA", size, data))

        width, height = (image.width, image.height)
        cls.draw_image(image,
                       (pos[0] + width * scale[0] * align[0] / 2, pos[1] + height * scale[1] * align[1] / 2),
                       (width * scale[0], height * scale[1]),
                       color=color,
                       alpha=alpha,
                       static=static)

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

    def get_texture(self) -> TextureData:
        return self.image["texture"]
    
    def set_id(self, id: int) -> None:
        self._id = id

    def get_id(self) -> int:
        return self._id
    
    def __str__(self) -> str:
        return f"{type(self).__name__} - {self._id}"

class EntityManager:
    _entities: dict[dict[Entity]] = {}
    _content_orders: list[int] = []
    _content_layers: dict[list[int]] = {}

    _pre_tick: dict[Entity] = {}
    _tick: dict[Entity] = {}
    _pos_tick: dict[Entity] = {}

    _layer_changes: dict[Entity, int] = {}
    _order_changes: dict[Entity, int] = {}
    _entity_changes: dict[Entity] = {}
    _ticks: dict[list[Entity]] = {}
    _id: int = 0

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
    def clear_agend(cls):
        cls._entity_changes = {}
        cls._order_changes = {}
        cls._layer_changes = {}

    @classmethod
    def create_entity(cls, entity: Entity, order: int, pre_tick: bool, tick: bool, pos_tick: bool) -> None:
        entity.set_id(cls._id)
        cls._id += 1
        if not order == -1:
            cls.add_entity_layer(entity)
        
        if pre_tick:
            
            cls.add_entity_tick(entity, 0)
        if tick:
            cls.add_entity_tick(entity, 1)
        if pos_tick:
            cls.add_entity_tick(entity, 2)

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
        if tick_type == 0:
            cls._pre_tick.remove(entity._id)
        elif tick_type == 1:
            cls._tick.remove(entity._id)
        elif tick_type == 2:
            cls._pos_tick.remove(entity._id)


    @classmethod
    def add_entity_layer(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if cls._entities.get(order) == None:
            cls._entities[order] = {layer: [entity]}
        else:
            if cls._entities[order].get(layer) == None:
                cls._entities[order][layer] = [entity]
            else:
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
    