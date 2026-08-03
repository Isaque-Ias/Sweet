import inspect
from ..core.linalg.vector import Vec3
from ..core.linalg.rotation import Rotation, RotationModel
from typing import Sequence, Callable, Any, Optional
from ..core import system
from ..resources.common import TRS
from .camera import Camera
from ..graphics.upload import GPUHandle

class GameModel:
    def __init__(self):
        pass

    def main(self):
        pass

class Entity:
    def __init__(self, name: str, children: list["Entity"] | None = None, parent: "Entity | None" = None):
        self.name = name
        self._parent = None

        self._children: list[Entity] = []
        
        self._parents: list[Entity] = []
        self._depth = 0
        self._mesh: Optional[str] = None

        self._transform = TRS(
            position = Vec3(0, 0, 0),
            rotation = Rotation(Vec3(), RotationModel.VECTOR),
            scale = Vec3(1, 1, 1),
        )

        self._script: Callable[..., None] | None = None

        if parent is not None:
            self.parent = parent
            
        if children:
            self.add_children(children)
        else:
            self._update_hierarchy_metadata()

    def set_mesh_component(self, pointer: GPUHandle) -> None:
        if pointer.defined:
            self._mesh = pointer.key

    def get_mesh(self) -> str | None:
        return self._mesh

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, value: Camera):
        self._camera = value

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, value: TRS):
        self._transform = value

    @property
    def position(self):
        return self._transform.position

    @position.setter
    def position(self, value: Sequence[float] | Vec3):
        self._transform.position = Vec3(*value)

    @property
    def scale(self):
        return self._transform.scale

    @scale.setter
    def scale(self, value: Sequence[float] | Vec3):
        self._transform.scale = Vec3.from_iter(value)

    @property
    def rotation(self):
        return self._transform.rotation

    @rotation.setter
    def rotation(self, value: Sequence[float] | Vec3, angle_model: RotationModel=RotationModel.VECTOR):
        self._transform.rotation = Rotation(Vec3.from_iter(value), angle_model)

    @property
    def children(self) -> list["Entity"]:
        return self._children

    @property
    def parent(self) -> "Entity | None":
        return self._parent
    
    @parent.setter
    def parent(self, value: "Entity | None"):
        if value is self._parent:
            return
            
        if self._parent is not None:
            self._parent.dettach_children(self)
            
        if value is None:
            self._parent = None
            self._update_hierarchy_metadata()
        else:
            value.add_children(self)

    @property
    def parents(self) -> list["Entity"]:
        return self._parents

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def sibling_index(self) -> int:
        if self._parent is None:
            return -1
        return self._parent.children.index(self)

    def add_children(self, children: Sequence["Entity"] | "Entity", index: int = -1):
        if isinstance(children, Entity):
            children = [children]

        existing_names = {child.name for child in self._children}

        for child in children:
            if child.name in existing_names:
                child.name = child.name + " (cópia)"
            
            if child._parent is not None and child._parent is not self:
                child._parent.dettach_children(child)

            child._parent = self
            if index == -1:
                self._children.append(child)
            else:
                self._children.insert(index, child)
                index += 1
                
            existing_names.add(child.name)
            
        self._update_hierarchy_metadata()

    def dettach_children(self, children: "list[Entity] | Entity") -> list["Entity"]:
        if isinstance(children, Entity):
            children = [children]

        detached: list["Entity"] = []
        for child in children:
            if child in self._children:
                self._children.remove(child)
                child._parent = None
                child._update_hierarchy_metadata()
                detached.append(child)

        return detached

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
            self.parent.dettach_children(self)

    def remove_children(self, children: Sequence["Entity"] | "Entity", heritance: bool = False):
        if isinstance(children, Entity):
            children = [children]

        for child in children:
            if child in self._children:
                child.destroy(heritance)
            else:
                system.warn(f"Nó '{child.name}' não pertence a essa entidade")

    def _update_hierarchy_metadata(self):
        parent_list: list["Entity"] = []
        reference_parent = self._parent
        depth = 0

        while reference_parent is not None:
            if reference_parent in parent_list or reference_parent is self:
                system.warn("Loop cíclico detectado na árvore. Abortando atualização")
                break
            parent_list.append(reference_parent)
            depth += 1
            reference_parent = reference_parent._parent

        self._parents = parent_list
        self._depth = depth

        for child in self._children:
            child._update_hierarchy_metadata()

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

    def inherit_model(self, model_class: type[GameModel], *args: list[Any], **kwargs: dict[str, Any]):
        model_instance = model_class(*args, **kwargs)
        
        for name, value in model_instance.__dict__.items():
            setattr(self, name, value)
            
        for name, attr in inspect.getmembers(model_class, predicate=inspect.isfunction):
            if name.startswith("__") and name.endswith("__"):
                continue

            self.attach_main_script(model_instance.main)
                
            bound_method = attr.__get__(self, Entity)
            setattr(self, name, bound_method)

    def get_script(self):
        return self._script