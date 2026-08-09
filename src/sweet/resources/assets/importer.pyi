from pathlib import Path
from .import_data import *

class ImportManager:
    @staticmethod
    def load_scene(path: str | Path) -> SceneData: ...

    @staticmethod
    def load_scenes(path: str | Path) -> dict[str, SceneData]: ...

    @staticmethod
    def load_assets(path: str | Path) -> AssetData: ...

    @staticmethod
    def load_model(path: str | Path, query: Optional[str]=None) -> Optional[MeshData]: ...

    @staticmethod
    def load_models(path: str | Path) -> dict[str, MeshData]: ...

    @staticmethod
    def load_texture(path: str | Path) -> Optional[TextureData]: ...

    @staticmethod
    def load_textures(path: str | Path) -> dict[str, TextureData]: ...

    @staticmethod
    def load_shaders(path_vertex: str | Path, path_fragment: str | Path) -> ShaderData: ...

    @staticmethod
    def load_compute_shaders(path: str | Path) -> ComputeData: ...