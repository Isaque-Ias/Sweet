from .shaders import ShaderHandler
import pygame as pg
from PIL import Image
from ..common import *
from pathlib import Path
from .imaging import Imaging

class Texture:
    _textures: dict[Imaging] = {}
    
    @classmethod
    def set_texture(cls, name: str, path: Path | str, save_type: FileType=FileType.PGSURF) -> None:
        if not cls._textures.get(path) == None:
            raise KeyError

        if save_type == FileType.PGSURF:
            surface: pg.Surface = pg.image.load(path)
            cls._textures[name] = Imaging(surface, FileType.PGSURF)
            return
        if save_type == FileType.PILIMAGE:
            surface: Image.Image = Image.open(path).convert("RGBA")
            cls._textures[name] = Imaging(surface, FileType.PILIMAGE)
            return
        if save_type == FileType.SHADERATLAS:
            surface: pg.Surface = pg.image.load(path).convert_alpha()
            cls._textures[name] = Imaging(*ShaderHandler.add_texture(surface))

    @classmethod
    def get_texture(cls, name: str) -> Imaging:
        return cls._textures[name]