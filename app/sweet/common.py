from typing import TypeAlias, Sequence
from enum import Enum, auto
import pygame as pg
from PIL import Image
from dataclasses import dataclass

class FileType(Enum):
    STREAM = auto()
    BATCHLIST = auto()
    BATCH = auto()
    DYNAMIC = auto()
    BACKGROUND = auto()
    NONE = auto()

class ConvertType(Enum):
    GIF = auto()
    VIDEO = auto()
    IMAGE = auto()

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

@dataclass
class Rec:
    x: int
    y: int
    w: int
    h: int

@dataclass
class UVLocation:
    tex_id: int = ""
    uv: Rec = None

@dataclass
class ShaderData:
    layout: dict
    vertex: str
    fragment: str
    program: object = None
    vbo: int = None
    vao: int = None
    ssbo: int = None
    stride_size: int = 0