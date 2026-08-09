from __future__ import annotations
from collections import defaultdict
import inspect
from abc import ABC, abstractmethod
from ..core.linalg.vector import Vec3, Vec4
from .components import Component
from ..core.linalg.rotation import Rotation, RotationModel
from .visual import Visual
from typing import Sequence, Callable, Any, Optional, TYPE_CHECKING
from ..core import system
from ..resources.common import TRS
from .camera import Camera

if TYPE_CHECKING:
    from .scene import Scene

class GameModel(ABC):
    
    @abstractmethod
    def __init__(self, **kwargs: Any):
        self._node: Entity

    @property
    def node(self) -> "Entity":
        return self._node

    @node.setter
    def node(self, node: Entity) -> None:
        self._node = node

    @abstractmethod
    def main(self):
        pass

class Entity:
    def __init__(self, name: str, children: list["Entity"] | None = None, parent: "Entity | None" = None):
        self.name = name
        self._parent: Optional["Entity"] = None
        self._scene: Optional[Scene] = None
        self._scene_index: Optional[int] = None
        self._components: dict[str, list[Any]] = defaultdict(list)
        self._aabb: list[float] = [0, 0, 0, 0, 0, 0]
        self._visuals: list[tuple[Optional[int], Visual]] = []

        self._children: list[Entity] = []
        self._depth: int = 0
    
        self._transform = TRS(
            position = Vec3(0, 0, 0),
            rotation = Rotation(Vec4(0, 0, 0, 1), RotationModel.QUATERNION),
            scale = Vec3(1, 1, 1),
        )

        self._script: Callable[..., None] | None = None

        if parent is not None:
            self.parent = parent

        if children:
            self.add_children(children)
        else:
            self._update_hierarchy_metadata()

    def attach_visual(self, visual: Visual) -> None:
        if visual not in list(map(lambda x: x[1], self._visuals)):
            parent_index = -1 if self._scene_index is None else self._scene_index
            index = None
            if self._scene:
                index = self._scene.data_track.allocate(visual, self._transform, visual.source.bounding, parent_index)
            self._visuals.append((index, visual))

    def attach_component(self, component: Component) -> None:
        self._components[str(component.__class__)].append(component)

    def dettach_component(self, component: Component) -> None:
        try:
            self._components[str(component.__class__)].remove(component)
        except ValueError:
            return

    def get_components(self, element: type) -> list[Component]:
        return self._components[str(element)]

    @property
    def scene(self):
        return self._scene

    def _assign_scene_recursive(self, scene: Optional[Scene]) -> None:
        if self._scene == scene:
            return

        if self._scene is not None and self._scene_index is not None:
            for i, visual_info in enumerate(self._visuals):
                index, visual = visual_info
                self._scene.data_track.free(index) # type: ignore
                self._visuals[i] = (None, visual)

            self._scene.data_track.free(self._scene_index)
            self._scene_index = None

        self._scene = scene

        if scene is not None:
            self._scene_index = scene.data_track.allocate(None, self._transform, self._aabb)
            
            for i, visual_info in enumerate(self._visuals):
                index, visual = visual_info
                if index is None:
                    index = self._scene.data_track.allocate(visual, self._transform, visual.source.bounding, self._scene_index) # type: ignore
                self._visuals[i] = (index, visual)


        for child in self._children:
            child._assign_scene_recursive(scene)

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, value: Camera):
        self._camera = value

    @property
    def position(self):
        return self._transform.position

    @position.setter
    def position(self, value: Sequence[float] | Vec3):
        self._transform.position = Vec3(*value)
        self._mark_transform_dirty()

    @property
    def scale(self):
        return self._transform.scale

    @scale.setter
    def scale(self, value: Sequence[float] | Vec3):
        self._transform.scale = Vec3(*value)
        self._mark_transform_dirty()

    @property
    def rotation(self):
        return self._transform.rotation

    @rotation.setter
    def rotation(self, value: Sequence[float] | Vec3, angle_model: RotationModel=RotationModel.VECTOR):
        self._transform.rotation = Rotation(Vec3.from_iter(value), angle_model).convert(RotationModel.QUATERNION)
        self._mark_transform_dirty()

    @property
    def children(self) -> list["Entity"]:
        return self._children

    @property
    def parent(self) -> Optional["Entity"]:
        return self._parent
    
    @parent.setter
    def parent(self, new_parent: Optional["Entity"]):
        if new_parent is self._parent:
            return
        
        if self._parent is not None:
            self._parent._children.remove(self)
            
        self._parent = new_parent
        
        if new_parent is None:
            self._update_hierarchy_metadata()
            if self._scene and self not in self._scene.entities:
                self._scene.entities.append(self)
        else:
            if self._scene and self in self._scene.entities:
                self._scene.entities.remove(self)
                
            if self not in new_parent._children:
                new_parent._children.append(self)
                
            self._assign_scene_recursive(new_parent.scene)
            self._update_hierarchy_metadata()

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def sibling_index(self) -> int:
        if self._parent is None:
            return -1
        return self._parent.children.index(self)

    def add_children(self, children: Sequence["Entity"] | "Entity"):
        if isinstance(children, Entity):
            children = [children]

        for child in children:
            child.parent = self 

    def dettach_children(self, children: list["Entity"] | "Entity") -> list["Entity"]:
        if isinstance(children, Entity):
            children = [children]

        detached: list[Entity] = []
        for child in children:
            if child in self._children:
                child.parent = None
                detached.append(child)
        return detached

    def _update_hierarchy_metadata(self):
        parent_list: list["Entity"] = []
        curr = self._parent
        while curr is not None:
            if curr in parent_list or curr is self:
                raise ValueError("Cyclic loop detected inside your transform hierarchy graph!")
            parent_list.append(curr)
            curr = curr._parent

        self._parents = parent_list
        self._depth = len(parent_list)

        for child in self._children:
            child._update_hierarchy_metadata()

    def destroy(self, heritance: bool = False) -> None:
        current_children = list(self._children)
        
        if heritance:
            if self.parent is None:
                self.dettach_children(current_children)
            else:
                self.parent.add_children(current_children)
        else:
            for child in current_children:
                child.destroy(heritance=False)

        if self.parent is not None:
            self.parent._children.remove(self)
            
        self._assign_scene_recursive(None)

    def _mark_transform_dirty(self):
        if self._scene is not None and self._scene_index is not None:
            self._scene.data_track.update_transform(
                self._scene_index,
                self._transform,
                self._aabb
            )

    def remove_children(self, children: Sequence["Entity"] | "Entity", heritance: bool = False):
        if isinstance(children, Entity):
            children = [children]

        for child in children:
            if child in self._children:
                child.destroy(heritance)
            else:
                system.warn(f"Nó '{child.name}' não pertence a essa entidade")

    @property
    def flatten_outline(self) -> list["Entity"]:
        entities: list["Entity"] = [self]
        for child in self._children:
            entities.extend(child.flatten_outline)
        return entities

    @property
    def flatten_leaves_first(self) -> list["Entity"]:
        entities: list["Entity"] = []
        for child in self._children:
            entities.extend(child.flatten_leaves_first)
        entities.append(self)
        return entities

    def is_root(self) -> bool:
        return True if self._depth == 0 else False

    def attach_main_script(self, script: Callable[..., None]):
        self._script = script

    def get_script(self):
        return self._script

    def inherit_model(self, model_class: type[GameModel], *args: Any, **kwargs: Any):
        model_instance = model_class(*args, **kwargs)
        model_instance.node = self
        
        for name, value in model_instance.__dict__.items():
            setattr(self, name, value)
            
        for name, attr in inspect.getmembers(model_class, predicate=inspect.isfunction):
            if name.startswith("__") and name.endswith("__"):
                continue

            self.attach_main_script(model_instance.main)
                
            bound_method = attr.__get__(self, Entity)
            setattr(self, name, bound_method)