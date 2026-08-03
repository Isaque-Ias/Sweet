from pathlib import Path
from .import_data import *

class ImportManager:
    @staticmethod
    def load_scene(path: str | Path) -> SceneData: ...

    @staticmethod
    def load_scenes(path: str | Path) -> list[SceneData]: ...

    @staticmethod
    def load_models(path: str | Path) -> list[MeshData]: ...

    @staticmethod
    def load_shaders(path_vertex: str | Path, path_fragment: str | Path) -> ShaderData: ...