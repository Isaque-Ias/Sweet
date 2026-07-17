from .graphics.texture import Imaging
from .graphics.shading import ShaderRender
from .graphics.mesh import Mesh
from .common import Sprite, FrameTransform, Transform
from math import pi

class Entity:
    def __init__(self, name: str) -> None:
        self.name = name
        self.transform = None
        self.children = []

        EntityManager.agend_entity(self)

    def pos_tick(self) -> None:
        pass

    def pre_tick(self) -> None:
        pass

    def tick(self) -> None:
        pass

    def draw(self) -> None:
        pass

    def set_id(self, id: int) -> None:
        self._id = id

    def get_id(self) -> int:
        return self._id

    def destroy_self(self):
        EntityManager.agend_destroy(self)

    def __str__(self) -> str:
        return f"{type(self).__name__} - {self._id}"


class EntityManager:
    _entities: dict[int, Entity] = {}

    _entity_changes: dict[Entity, Entity] = {}
    _destroy_changes: dict[Entity, Entity] = {}
    _id: int = 0

    @classmethod
    def update_transform_lerp(cls):
        for entity in cls._entities.values():
            entity.transform.alpha = entity.transform.current

    @classmethod
    def update_transforms(cls):
        for entity in cls._entities.values():
            entity.transform.current = Transform(
                pos=entity.pos,
                scale=entity.scale,
                angle=entity.angle,
            )

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
    def agend_entity(cls, entity: Entity):
        cls._entity_changes[entity] = entity

    @classmethod
    def agend_destroy(cls, entity: Entity):
        cls._destroy_changes[entity] = entity

    @classmethod
    def clear_agend(cls):
        cls._entity_changes = {}
        cls._layer_changes = {}
        cls._destroy_changes = {}

    @classmethod
    def create_entity(cls, entity: Entity) -> None:
        entity.set_id(cls._id)
        cls._id += 1

        cls._entities[entity.get_id()] = entity

    @classmethod
    def destroy_entity(cls, entity: Entity):
        entity_id = entity.get_id()
        if entity_id in cls._entities:
            del cls._entities[entity_id]

    @classmethod
    def get_all_entities(cls) -> dict[int, Entity]:
        return cls._entities

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
        model: Mesh,
        image: Imaging | None,
        transform: FrameTransform,
        color: tuple[int | float, int | float, int | float, int | float] = (
            255,
            255,
            255,
            255,
        ),
    ) -> None:

        color = (color[0] / 255, color[1] / 255, color[2] / 255, color[3] / 255)
        transform.current.angle *= pi / 180
        sprite = Sprite(
            model.name,
            image if image is None else image.uv,
            transform,
            color,
            cls._state_shader,
            cls._state_attr,
        )

        ShaderRender.add_draw_call(sprite)
