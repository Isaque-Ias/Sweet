from .graphics.texture import Imaging
from .graphics.shaders import ShaderRender
from .graphics.model import ModelInstance
from .common import Sprite
from .vector import Vec2, Vec3
from math import pi


class Entity:
    def __init__(
        self,
        pos: tuple[int, int] | tuple[int, int, int] = (0, 0),
        scale: tuple[int, int] | tuple[int, int, int] = (1, 1),
        angle: float | tuple[float, float, float] = 0,
        pre_tick: bool = False,
        tick: bool = False,
        pos_tick: bool = False,
    ) -> None:

        self.__flat = False
        if len(pos) == 0:
            self.__flat = True

        if self.__flat:
            self.pos = Vec2(*pos)
            self.scale = Vec2(*scale)
            self.angle = angle
        else:
            self.pos = Vec3(*pos)

            if len(scale) == 2:
                self.scale = Vec3(scale[0], scale[1], 1)
            else:
                self.scale = Vec3(*scale)

            if isinstance(angle, float) or isinstance(angle, int):
                self.angle = Vec3(angle, 0, 0)
            else:
                self.angle = Vec3(*angle)

        EntityManager.agend_entity(self, pre_tick, tick, pos_tick)

    def pos_tick(self) -> None:
        pass

    def pre_tick(self) -> None:
        pass

    def tick(self) -> None:
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
    _entities: dict[int, Entity] = {}

    _pre_tick: dict[int, Entity] = {}
    _tick: dict[int, Entity] = {}
    _pos_tick: dict[int, Entity] = {}

    _entity_changes: dict[Entity, tuple[Entity, bool, bool, bool]] = {}
    _destroy_changes: dict[Entity, Entity] = {}
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
    def get_entity_changes(cls):
        return cls._entity_changes

    @classmethod
    def get_destroy_changes(cls):
        return cls._destroy_changes

    @classmethod
    def agend_entity(cls, entity: Entity, pre_tick: bool, tick: bool, pos_tick: bool):
        cls._entity_changes[entity] = (entity, pre_tick, tick, pos_tick)

    @classmethod
    def agend_destroy(cls, entity: Entity):
        cls._destroy_changes[entity] = entity

    @classmethod
    def clear_agend(cls):
        cls._entity_changes = {}
        cls._layer_changes = {}
        cls._destroy_changes = {}

    @classmethod
    def create_entity(
        cls, entity: Entity, pre_tick: bool, tick: bool, pos_tick: bool
    ) -> None:
        entity.set_id(cls._id)
        cls._id += 1

        if pre_tick:
            cls.add_entity_tick(entity, 0)
        if tick:
            cls.add_entity_tick(entity, 1)
        if pos_tick:
            cls.add_entity_tick(entity, 2)

        cls._entities[entity.get_id()] = entity

    @classmethod
    def destroy_entity(cls, entity: Entity) -> None:
        cls.remove_entity_tick(entity, 0)
        cls.remove_entity_tick(entity, 1)
        cls.remove_entity_tick(entity, 2)

    @classmethod
    def add_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0:
            cls._pre_tick[entity.get_id()] = entity
        elif tick_type == 1:
            cls._tick[entity.get_id()] = entity
        elif tick_type == 2:
            cls._pos_tick[entity.get_id()] = entity

    @classmethod
    def remove_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0 and not cls._pre_tick.get(entity.get_id()) is None:
            cls._pre_tick.pop(entity.get_id())
        elif tick_type == 1 and not cls._tick.get(entity.get_id()) is None:
            cls._tick.pop(entity.get_id())
        elif tick_type == 2 and not cls._pos_tick.get(entity.get_id()) is None:
            cls._pos_tick.pop(entity.get_id())

    @classmethod
    def get_all_entities(cls) -> dict[int, Entity]:
        return cls._entities

    @classmethod
    def get_tick_entities(cls, tick_type: int) -> dict[int, Entity]:
        if tick_type == 0:
            return cls._pre_tick
        elif tick_type == 1:
            return cls._tick
        elif tick_type == 2:
            return cls._pos_tick
        raise ValueError("Insira um tipo válido.")


class Draw:
    _state_attr: dict[str, tuple[int | float, ...]] = {}
    _state_shader: str = "__def__"

    @classmethod
    def set_state_shader(cls, name: str) -> None:
        cls._state_shader = name
        cls.clear_state_shader()

    @classmethod
    def clear_state_shader(cls):
        cls._state_attr = {}

    @classmethod
    def set_shader_attr(cls, name: str, *values: int | float) -> None:
        cls._state_attr[name] = values

    @classmethod
    def draw_image(
        cls,
        model: ModelInstance,
        image: Imaging | None,
        pos: Vec3,
        scale: Vec3,
        angle: Vec3,
        color: tuple[int | float, int | float, int | float, int | float] = (
            255,
            255,
            255,
            255,
        ),
    ) -> None:

        color = (color[0] / 255, color[1] / 255, color[2] / 255, color[3] / 255)
        angle = Vec3(angle.x * pi / 180, angle.y * pi / 180, angle.z * pi / 180)

        sprite = Sprite(
            model.name,
            image if image is None else image.uv,
            pos.unp(),
            scale.unp(),
            angle.unp(),
            color,
            cls._state_shader,
            cls._state_attr,
        )

        ShaderRender.add_draw_call(sprite)
