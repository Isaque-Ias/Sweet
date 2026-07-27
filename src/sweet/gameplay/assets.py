from pathlib import Path
from..resources.assets.importer import ImportManager
from..resources.assets.import_data import NodeData, SceneData
from .scene import SceneManager, Scene
from .entity import Entity
from typing import Optional
from ..graphics.upload import UploadManager

class Assets:
    @classmethod
    def convert_to_entity(cls, node: NodeData, content: SceneData, parent: Optional[Entity] = None) -> Entity:
        entity_children: list[Entity] = []
        for child in node.children:
            converted_child = cls.convert_to_entity(child, content, parent)
            entity_children.append(converted_child)

        entity = Entity(node.name, entity_children, parent)
        if node.mesh:
            mesh_data = content.meshes[node.mesh]
            handle = UploadManager.upload_mesh(mesh_data)
            entity.set_mesh_component(handle)

        return entity

    @classmethod
    def load_scene(cls, path: str | Path) -> Scene:
        scene = ImportManager.load_scene(path)

        children = scene.nodes
        entities: list[Entity] = []
        for child in children:
            entity_tree = cls.convert_to_entity(child, scene)
            entities.append(entity_tree)
        
        return SceneManager.new_scene(scene.name, entities)