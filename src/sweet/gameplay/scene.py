from ..core import system
from typing import Sequence, Callable, Optional
from ..resources.common import TRS
from .entity import Entity
from .visual import Visual
from .skybox import SkyBox
from .light import Light
from sweet.plataform.hal.manager import ResourceType
import numpy as np
from ..plataform.hal.manager import GraphicsDevice

graphics_device: GraphicsDevice

class SceneDataTrack:
    def __init__(self, initial_capacity: int=1024):
        self.capacity = initial_capacity
        self.size = 0

        self.layout = graphics_device.create_resource_layout([
            (2, ResourceType.STORAGE_BUFFER),
            (3, ResourceType.STORAGE_BUFFER),
            (4, ResourceType.STORAGE_BUFFER)
        ])
        self.set = graphics_device.create_resource_set(self.layout)

        self.transform_size = 10
        self.bounding_size = 6
        self.command_size = 5

        self.transform_stride = self.transform_size * 4
        self.bounding_stride = self.bounding_size * 4
        self.command_stride = self.command_size * 4
        
        self.parent_ids = np.full(self.capacity, -1, dtype=np.int32)

        self.free_indices: list[int] = []
        self.dirty_indices: set[int] = set()

        self.index_refs: dict[int, Visual] = {}

        self.dirty_min = float('inf')
        self.dirty_max = -1
    
        self.gpu_buffer = graphics_device.create_uniform_buffer(self.capacity * self.transform_stride)
        self.transforms = np.zeros((self.capacity, self.transform_size), dtype=np.float32)

        self.gpu_bounding = graphics_device.create_uniform_buffer(self.capacity * self.bounding_stride)
        self.boundings = np.zeros((self.capacity, self.bounding_size), dtype=np.float32)

        self.gpu_commands = graphics_device.create_uniform_buffer(self.capacity * self.command_stride)

    def allocate(self, ref: Optional[Visual], initial_trs: Optional[TRS]=None, aabb: Optional[list[float]] = None, parent: int = -1) -> int:
        if aabb is None:
            aabb = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        if self.free_indices:
            index = self.free_indices.pop()
        else:
            if self.size >= self.capacity:
                self._resize()
            index = self.size
            self.size += 1

        if initial_trs is not None:
            self.transforms[index] = [
                *initial_trs.position, 
                *initial_trs.rotation.scalars, 
                *initial_trs.scale
            ]
        else:
            self.transforms[index] = [0, 0, 0,  0, 0, 0, 1,  1, 1, 1]

        if parent == -1:
            parent = index
            
        self.parent_ids[index] = parent

        self.boundings[index] = aabb

        self.dirty_min = min(self.dirty_min, index)
        self.dirty_max = max(self.dirty_max, index)

        if ref:
            self.index_refs[index] = ref

        return index

    def free(self, index: int):
        self.free_indices.append(index)
        self.transforms[index] = 0.0
        self.boundings[index] = 0.0

        del self.index_refs[index]

        self.dirty_min = min(self.dirty_min, index)
        self.dirty_max = max(self.dirty_max, index)

    def update_transform(self, index: int, trs: TRS, aabb: Optional[list[float]]=None):
        if aabb is None:
            aabb = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        self.transforms[index] = [
            *trs.position, 
            *trs.rotation.scalars, 
            *trs.scale
        ]
        self.boundings[index] = aabb

        self.dirty_min = min(self.dirty_min, index)
        self.dirty_max = max(self.dirty_max, index)

    def flush_to_gpu(self):
        if self.dirty_max == -1:
            return

        offset = self.dirty_min * self.transform_stride
        dirty_slice = self.transforms[self.dirty_min : self.dirty_max + 1]
        self.gpu_buffer.upload_data(dirty_slice.tobytes(), offset=offset) # type: ignore

        offset = self.dirty_min * self.bounding_stride
        dirty_slice = self.boundings[self.dirty_min : self.dirty_max + 1]
        self.gpu_bounding.upload_data(dirty_slice.tobytes(), offset=offset) # type: ignore

        self.dirty_min = float("inf")
        self.dirty_max = -1

    def _resize(self):
        self.capacity *= 2
        new_transforms = np.zeros((self.capacity, self.transform_size), dtype=np.float32)
        new_boundings = np.zeros((self.capacity, self.bounding_size), dtype=np.float32)

        new_transforms[:self.size] = self.transforms
        self.transforms = new_transforms

        new_boundings[:self.size] = self.boundings
        self.boundings = new_boundings

        self.gpu_buffer.release()
        self.gpu_buffer = graphics_device.create_uniform_buffer(self.capacity * self.transform_stride)

        self.gpu_bounding.release()
        self.gpu_bounding = graphics_device.create_uniform_buffer(self.capacity * self.bounding_stride)

        self.gpu_commands.release()
        self.gpu_commands = graphics_device.create_uniform_buffer(self.capacity * self.command_stride)

        new_parent_ids = np.full(self.capacity, -1, dtype=np.int32)
        new_parent_ids[:self.size] = self.parent_ids
        self.parent_ids = new_parent_ids

        self.dirty_min = 0
        self.dirty_max = self.size - 1

class Scene:
    def __init__(self,
                 name: str = "[Sem nome]",
                 entities: Optional[list[Entity]] = None
        ):
        self.data_track = SceneDataTrack()
        self._name = name
        self._entities: list[Entity] = []
        self._active = False
        self._skybox: Optional[SkyBox] = None

        if entities is not None:
            self.add_entity(entities)

        SceneManager.add_scene(self)

    @property
    def skybox(self):
        return self._skybox

    @skybox.setter
    def skybox(self, skybox: SkyBox):
        self._skybox = skybox
        skybox.scene = self
        for view in skybox.views:
            view.set_scene(self)

    def get_lights(self):
        lights: list[Light] = []
        for root in self._entities:
            for entity in root.flatten_leaves_first:
                lights.extend(entity.get_lights())

        return lights

    def add_entity(self, entity: Sequence[Entity] | Entity):
        entity_list = [entity] if isinstance(entity, Entity) else entity

        existing_names = {e.name for e in self._entities}

        for element in entity_list:
            if element.name in existing_names:
                system.warn(f"Nó '{element.name}' já pertence a essa cena como raiz")
                continue
                
            self._entities.append(element)
            element._assign_scene_recursive(self) # type: ignore
            existing_names.add(element.name)

    def remove_entity(self, entity: Entity):
        if entity in self._entities:
            self._entities.remove(entity)
        entity._assign_scene_recursive(None) # type: ignore

    def print_tree(self):
        for entity in self._entities:
            print([e.name for e in entity.flatten_outline])

    def activate(self):
        self._active = True
        SceneManager.activate_scene(self)

    def deactivate(self):
        self._active = False
        SceneManager.deactivate_scene(self)

    def is_active(self):
        return self._active

    def apply_logic(self, logic: Callable[..., None]):
        all_nodes: list[Entity] = []
        for root_node in self._entities:
            all_nodes.extend(root_node.flatten_outline)
        
        logic(all_nodes)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def entities(self):
        return self._entities

class SceneManager:
    _scenes: dict[str, Scene] = {}
    _active_scenes: dict[str, Scene] = {}

    @classmethod
    def add_scene(cls, scene: Scene):
        if cls._scenes.get(scene.name) is None:
            cls._scenes[scene.name] = scene
            return

        system.problem(f"Já existe uma cena com o nome '{scene.name}'")

    @classmethod
    def activate_scene(cls, scene: Scene):
        if cls._active_scenes.get(scene.name) is None:
            cls._active_scenes[scene.name] = scene
            return
        
        system.warn("Cena já está ativada")

    @classmethod
    def deactivate_scene(cls, scene: Scene):
        del cls._scenes[scene.name]
    
    @classmethod
    def get_active_scenes(cls):
        return cls._active_scenes