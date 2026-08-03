from pathlib import Path
from..resources.assets.importer import ImportManager
from..resources.assets.import_data import NodeData, SceneData
from .scene import SceneManager, Scene
from .entity import Entity
from typing import Optional
from ..graphics.upload import UploadManager
from ..plataform.hal.manager import GraphicsDevice

class Assets:
    def __init__(self, graphics_device: GraphicsDevice):
        self._gfx_device = graphics_device
        UploadManager.set_graphics_device(self._gfx_device)

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
            # for primitive in mesh_data.primitives:
            #     if primitive.material is None:
            #         continue

            #     for texture in content.materials[primitive.material].texture_coordinate_map.values():
            #         pass

        return entity

    @classmethod
    def load_scene(cls, path: str | Path) -> Scene:
        scene = ImportManager.load_scene(path)

        children = scene.nodes
        entities: list[Entity] = []
        for child in children:
            entity_tree = cls.convert_to_entity(child, scene)
            entities.append(entity_tree)

        for texture in scene.textures.values():
            UploadManager.upload_texture_data(texture)
        
        return SceneManager.new_scene(scene.name, entities)