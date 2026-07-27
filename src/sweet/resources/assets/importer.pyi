from pathlib import Path
from .import_data import SceneData

class ImportManager:
    @staticmethod
    def load_scene(path: str | Path) -> SceneData: ...

    @staticmethod
    def load_scenes(path: str | Path) -> list[SceneData]: ...