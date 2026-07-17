import numpy as np
from ..common import Geometry
import trimesh
from pathlib import Path
from .shading import ShaderModels
from ..system import System
import json

class MeshManager:
    _models: dict[str, "Mesh"] = {}

    @classmethod
    def load_file(cls, path: str | Path):
        solved_path = System.solve_path(path)

        if not solved_path.exists():
            System.warn(f"Recursos não encontrados em ' {solved_path}")
            return
        
        if not solved_path.suffix == ".json":
            System.warn(f"Formato de recurso em '{solved_path}' não suportado")
            return

        with open(solved_path, "r") as file:
            assets = json.load(file)
            
        for asset_type in assets.keys():
            if asset_type == "scene":
                models = assets[asset_type]
                for key in models.keys():
                    path = models[key]
                    absolute_path = System.solve_path(path)

                    cls.resolve_file(key, absolute_path)

    @classmethod
    def resolve_file(cls, name: str, path: Path) -> "Mesh":
        if not cls._models.get(name) is None:
            report_config = System.config.resources.importing.report
            config = System.config.resources.importing.replace_old_assets
            if config == "__default__":
                raise KeyError(f"Modelo com chave '{name}' já existe. Para substituir, habilite a opção 'replace_old_assets' nas configurações")
                
            elif config == True:
                if report_config == True:
                    System.warn(f"Modelo com chave '{name}' já existe. Substituindo pelo novo modelo...")
                return cls.set_model(name, path)

            elif config == False:
                return cls.get_model(name)
        
        return cls.set_model(name, path)
    
    @staticmethod
    def get_fallback_path():
        config = System.config.resources.importing.fallback_model
        if config == "__default__":
            BASE = Path(__file__).parent
            fallback_path = BASE.parent / "build" / "__fallback__.obj"
        else:
            fallback_path = System.solve_path(config)
            if not fallback_path.exists():
                raise FileNotFoundError(f"Modelo de fallback não encontrada em: {fallback_path}")

        return fallback_path

    @classmethod
    def set_model(cls, name: str, path: Path) -> "Mesh":
        if not path.exists():
            report_config = System.config.resources.importing.report
            if report_config:
                System.warn("Modelo não encontrado: '" + str(name) + "' no caminho: " + str(path))
            path = cls.get_fallback_path()

        if path.suffix in [".obj"]:
            cls._models[name] = cls.open_file(name, path)
            cls._models[name].upload()
            return cls._models[name]
        else:
            raise FileNotFoundError(f"Não há suporte para modelos com o formato \" {path.suffix} \".")

    @staticmethod
    def _load_file(name: str, path: Path) -> "Mesh":
        mesh = trimesh.load(path) # type: ignore
        
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        vertices = mesh.vertices.astype(np.float32) # type: ignore
        normals = mesh.vertex_normals.astype(np.float32) # type: ignore
        faces = mesh.faces.astype(np.uint32) # type: ignore

        if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None: # type: ignore
            uvs = mesh.visual.uv.astype(np.float32) # type: ignore
        else:
            uvs = np.zeros((len(vertices), 2), dtype=np.float32)

        interleaved_data = np.hstack((vertices, uvs, normals)).astype(np.float32)

        vbo_data = interleaved_data.flatten()
        ebo_data = faces.flatten() # type: ignore
        index_count = len(ebo_data)
        geometry = Geometry(vbo_data=vbo_data, ebo_data=ebo_data, index_count=index_count) # type: ignore

        return Mesh(name, geometry)

    @classmethod
    def get_model(cls, name: str):
        if cls._models.get(name) is None:
            report_config = System.config.resources.importing.report
            if report_config:
                System.warn(f"Modelo não encontrado: '{name}'")
            path = cls.get_fallback_path()
            file = cls.open_file(name, path)
            file.upload()
            return file
        return cls._models[name]
    
    @classmethod
    def delete_model(cls, name: str):
        if cls._models.get(name) is None:
            report_config = System.config.resources.importing.report
            if report_config:
                System.warn(f"Modelo com o nome '{name}' não existe")
        del cls._models[name]

class Mesh:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.normals = []
        self.uvs = []
        self.material_id = []

    def upload(self):
        ShaderModels.add_model(self.name, self.geometry)