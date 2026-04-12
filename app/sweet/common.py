from typing import TypeAlias, Sequence
from enum import Enum, auto
import pygame as pg
from PIL import Image

class FileType(Enum):
    PGSURF = auto()
    PILIMAGE = auto()
    SHADERATLAS = auto()

class SurfaceTexture(Enum):
    PGSURF = auto()
    PILIMAGE = auto()

class PathType(Enum):
    PIECEWISE = auto()
    BEZIER = auto()

class Interpolation(Enum):
    QUAD_OUT = auto()
    QUAD_IN = auto()
    QUAD = auto()
    NONE = auto()

Draw: TypeAlias = pg.Surface | Image.Image | int
TextureData: TypeAlias = dict[Draw, int, int]
AtlasTexture: TypeAlias = dict[int, int, int]
Vector: TypeAlias = list[int, int]
Controls: TypeAlias = Sequence[Vector] | Sequence[list[Vector, Vector, Vector]]