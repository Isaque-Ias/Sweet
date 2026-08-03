from ..core import system
from typing import Sequence, Callable
from .entity import Entity

class Scene:
    def __init__(self, name: str = "[Sem nome]", entities: list[Entity] = []):
        self._entities = entities
        self._name = name
        self._active = False

    def print_tree(self):
        for entity in self._entities:
            print(entity.flatten_outline)

    def activate(self):
        self._active = True
        SceneManager.activate_scene(self)

    def deactivate(self):
        self._active = False
        SceneManager.deactivate_scene(self)

    def is_active(self):
        return self._active

    def apply_logic(self, logic: Callable[..., None]):
        for node in self._entities:
            nodes = node.flatten_outline
            logic(nodes)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def entities(self):
        return self._entities

    def add_entity(self, entity: Sequence[Entity] | Entity, index: int=-1):
        Entity_list: list[Entity] = []
        if isinstance(entity, Entity):
            Entity_list.append(entity)
        else:
            for element in entity:
                Entity_list.append(element)

        for element in Entity_list:
            if not element.name in map(lambda a: a.name, self._entities):
                self._entities.insert(index, element)
            else:
                system.warn(f"Nó '{element.name}' já pertence a essa cena")

class SceneManager:
    _scenes: list[Scene] = []
    _active_scenes: list[Scene] = []

    @classmethod
    def new_scene(cls, name: str, children: list[Entity] = []):
        scene = Scene(name, children)
        cls._scenes.append(scene)
        return scene

    @classmethod
    def activate_scene(cls, scene: Scene):
        if scene in cls._active_scenes:
            system.warn("Cena já está ativada")
            return

        cls._active_scenes.append(scene)

    @classmethod
    def deactivate_scene(cls, scene: Scene):
        try:
            cls._scenes.remove(scene)
        except ValueError:
            system.warn("Cena já está desativada")
    
    @classmethod
    def get_active_scenes(cls):
        return cls._active_scenes