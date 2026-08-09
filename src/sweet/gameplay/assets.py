from pathlib import Path
from..resources.assets.importer import ImportManager
from..resources.assets.import_data import NodeData, SceneData, MaterialData
from .scene import Scene
from .entity import Entity
from typing import Optional
from ..graphics.upload import UploadManager, GPUTexture, GPUSource
from ..plataform.hal.manager import GraphicsDevice
from dataclasses import dataclass
from .visual import Visual
from .material import Material, PBRMaterial#, PBRBaseLayer, PBREmissiveLayer, PBRSpecularLayer, PBRTransmissionLayer

@dataclass
class AssetSet:
    meshes: dict[str, list[GPUSource]]
    textures: dict[str, GPUTexture]
    materials: dict[str, Material]

class Assets:
    @classmethod
    def initialize(cls, graphics_device: GraphicsDevice):
        cls._gfx_device = graphics_device

    @classmethod
    def _load_material(cls, material_data: MaterialData) -> Material:
        # pbr = material_data.pbr_characteristics
        # idx = pbr.base_color_texture.texture_index if pbr.base_color_texture is not None else 0
        # material_data.texture_coordinate_map
        material = PBRMaterial()
        # material.base = PBRBaseLayer(
        #     color_texture=,
        # )
        alpha_mode = material_data.alpha_mode
        material.alpha_mode = alpha_mode

        return material

    @classmethod
    def convert_to_entity(cls, node: NodeData, content: SceneData, parent: Optional[Entity] = None, mesh_set: Optional[dict[str, list[GPUSource]]] = None, material_set: Optional[dict[str, Material]] = None) -> Entity:
        if material_set is None:
            material_set = {}
        if mesh_set is None:
            mesh_set = {}

        entity_children: list[Entity] = []
        for child in node.children:
            converted_child = cls.convert_to_entity(child, content, parent, mesh_set, material_set)
            entity_children.append(converted_child)

        entity = Entity(node.name, entity_children, parent)

        source_material_map: dict[str, Material] = {}
        if not node.mesh is None:
            mesh_data = content.meshes[node.mesh]
            sources = UploadManager.upload_mesh(mesh_data)
            mesh_set[mesh_data.name] = sources

            for prim in mesh_data.primitives:
                if prim.material is None:
                    continue
                material_data = content.materials[prim.material]
                material = cls._load_material(material_data)
                
                material_set[material_data.name] = material
                source_material_map[mesh_data.name] = material

            for source in sources:
                source_material = source_material_map[mesh_data.name]
                visual = Visual(source, source_material)
                entity.attach_visual(visual)

        return entity

    @classmethod
    def load_scene(cls, path: str | Path) -> tuple[AssetSet, Scene]:
        scene = ImportManager.load_scene(path)

        children = scene.nodes
        mesh_set: dict[str, list[GPUSource]] = {}
        material_set: dict[str, Material] = {}
        entities: list[Entity] = []
        for child in children:
            entity_tree = cls.convert_to_entity(child, scene, mesh_set=mesh_set, material_set=material_set)
            entities.append(entity_tree)

        texture_set: dict[str, GPUTexture] = {}
        for texture in scene.textures.values():
            texture_source = UploadManager.upload_texture(texture)
            texture_set[texture.name] = texture_source

        assets = AssetSet(
            meshes=mesh_set,
            textures=texture_set,
            materials=material_set
        )
        
        scene = Scene(
            name=scene.name,
            entities=entities
        )

        return assets, scene

    @classmethod
    def load_model(cls, path: str | Path) -> list[GPUSource]:
        model = ImportManager.load_model(path)
        if model is None:
            raise ImportError(f"Falha ao importar mesh em '{path}'")
        sources = UploadManager.upload_mesh(model)
        return sources
    
    @classmethod
    def load_models(cls, path: str | Path) -> dict[str, list[GPUSource]]:
        sources: dict[str, list[GPUSource]] = {}
        models = ImportManager.load_models(path)
        
        for model in models.values():
            source = UploadManager.upload_mesh(model)
            sources[model.name] = source
        
        return sources
    
    @classmethod
    def load_textures(cls, path: str | Path) -> dict[str, GPUTexture]:
        sources: dict[str, GPUTexture] = {}
        textures = ImportManager.load_textures(path)
        for texture in textures.values():
            source = UploadManager.upload_texture(texture)
            sources[texture.name] = source
        
        return sources

    @classmethod
    def load_texture(cls, path: str | Path) -> GPUTexture:
        texture = ImportManager.load_texture(path)
        if texture is None:
            raise ImportError(f"Falha ao importar textura em '{path}'")
        texture_source = UploadManager.upload_texture(texture)
        return texture_source

    @classmethod
    def load_assets(cls, path: str | Path) -> AssetSet:
        asset_data = ImportManager.load_assets(path)
        texture_sources: dict[str, GPUTexture] = {}
        mesh_sources: dict[str, list[GPUSource]] = {}
        material_sources: dict[str, Material] = {}

        for texture in asset_data.textures.values():
            source = UploadManager.upload_texture(texture)
            texture_sources[texture.name] = source

        for mesh in asset_data.meshes.values():
            source = UploadManager.upload_mesh(mesh)
            mesh_sources[mesh.name] = source

        for material in asset_data.materials.values():
            source = cls._load_material(material)
            material_sources[material.name] = source

        asset_set = AssetSet(
            meshes=mesh_sources,
            textures=texture_sources,
            materials=material_sources
        )
        return asset_set