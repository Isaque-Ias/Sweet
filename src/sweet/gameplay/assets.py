from pathlib import Path
from..resources.assets.importer import ImportManager
from..resources.assets.import_data import NodeData, SceneData, MaterialData
from .scene import Scene
from .entity import Entity
from typing import Optional
from ..graphics.upload import UploadManager, GPUTexture, GPUSource, GPUMaterial
from ..plataform.hal.manager import GraphicsDevice
from dataclasses import dataclass
from .visual import Visual

@dataclass
class AssetSet:
    meshes: dict[str, list[GPUSource]]
    textures: dict[str, GPUTexture]
    materials: dict[str, GPUMaterial]

class Assets:
    @classmethod
    def initialize(cls, graphics_device: GraphicsDevice):
        cls._gfx_device = graphics_device

    @classmethod
    def _load_material(cls, material_data: MaterialData, texture_cache: dict[int, GPUTexture], orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture]) -> GPUMaterial:
        gpu_material = UploadManager.upload_material(material_data, texture_cache, orm_cache)

        return gpu_material # type: ignore

    @classmethod
    def convert_to_entity(cls, node: NodeData, content: SceneData, parent: Optional[Entity] = None, mesh_set: Optional[dict[str, list[GPUSource]]] = None, material_set: Optional[dict[str, GPUMaterial]] = None, texture_cache: Optional[dict[int, GPUTexture]] = None, orm_cache: Optional[dict[tuple[Optional[int], Optional[int]], GPUTexture]] = None) -> Entity:
        if material_set is None:
            material_set = {}
        if mesh_set is None:
            mesh_set = {}
        if texture_cache is None:
            texture_cache = {}
        if orm_cache is None:
            orm_cache = {}

        entity_children: list[Entity] = []
        for child in node.children:
            converted_child = cls.convert_to_entity(child, content, parent, mesh_set, material_set, texture_cache, orm_cache)
            entity_children.append(converted_child)

        entity = Entity(node.name, entity_children, parent)

        if not node.mesh is None:
            mesh_data = content.meshes[node.mesh]
            sources = UploadManager.upload_mesh(mesh_data)
            mesh_set[mesh_data.name] = sources

            for prim, source in zip(mesh_data.primitives, sources):
                material = None
                if prim.material is not None:
                    material_data = content.materials[prim.material]
                    material = cls._load_material(material_data, texture_cache, orm_cache)
                    material_set[material_data.name] = material

                visual = Visual(source, material)
                entity.attach_visual(visual)

        return entity

    @classmethod
    def load_scene(cls, path: str | Path) -> tuple[AssetSet, Scene]:
        scene = ImportManager.load_scene(path)
        children = scene.nodes
        mesh_set: dict[str, list[GPUSource]] = {}
        material_set: dict[str, GPUMaterial] = {}
        texture_cache: dict[int, GPUTexture] = {}
        orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture] = {}
        entities: list[Entity] = []
        for child in children:
            entity_tree = cls.convert_to_entity(child, scene, mesh_set=mesh_set, material_set=material_set, texture_cache=texture_cache, orm_cache=orm_cache)
            entities.append(entity_tree)

        texture_set: dict[str, GPUTexture] = {tex.name: texture_cache[id(tex)] for tex in scene.textures.values() if id(tex) in texture_cache}

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
        material_sources: dict[str, GPUMaterial] = {}

        texture_cache: dict[int, GPUTexture] = {}
        orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture] = {}

        for mesh in asset_data.meshes.values():
            source = UploadManager.upload_mesh(mesh)
            mesh_sources[mesh.name] = source

        for material in asset_data.materials.values():
            source = UploadManager.upload_material(material, texture_cache, orm_cache)
            material_sources[material.name] = source # type: ignore

        for texture in asset_data.textures.values():
            if id(texture) in texture_cache:
                texture_sources[texture.name] = texture_cache[id(texture)]

        asset_set = AssetSet(
            meshes=mesh_sources,
            textures=texture_sources,
            materials=material_sources
        )
        return asset_set