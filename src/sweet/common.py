from enum import Enum, auto
from dataclasses import dataclass, field
from .vector import Vec2
import numpy as np
import moderngl

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

@dataclass
class Rec:
    x: int
    y: int
    w: int
    h: int

@dataclass
class UVLocation:
    texture: str | None = None
    uv: Rec = field(default_factory=lambda: Rec(0, 0, 0, 0))

@dataclass
class CollisionData:
    mtv: Vec2
    normal: Vec2
    is_b: bool
    contact_point: Vec2
    entity: object

@dataclass
class Sprite:
    model: str
    texture: UVLocation | None
    pos: tuple[float, float, float]
    scale: tuple[float, float, float]
    rotation: tuple[float, float, float]
    color: tuple[float, float, float, float]
    shader: str
    attrs: dict[str, tuple[int | float, ...]]

@dataclass
class Geometry:
    vbo_data: np.ndarray
    ebo_data: np.ndarray
    index_count: int
    vao: moderngl.VertexArray | None = None
@dataclass
class Object:
    mesh: Geometry
    texture: UVLocation
    pos: tuple[float, float, float]
    scale: tuple[float, float, float]
    rotation: tuple[float, float, float]
    color: tuple[float, float, float, float]
    perspective: bool
    static: bool
    shader: str
    attrs: dict[str, tuple[int | float, ...]]
