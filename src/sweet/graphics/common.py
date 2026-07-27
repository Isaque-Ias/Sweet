from dataclasses import dataclass, field
import moderngl

@dataclass
class FrameBuffer:
    texture: moderngl.Texture
    buffer: moderngl.Framebuffer
    components: int

@dataclass
class BufferInfo:
    buffer: moderngl.Buffer
    capacity: int 

@dataclass
class LayoutInfo:
    name: str
    component_type: str
    component_size: str

@dataclass
class MeshBuffer:
    layout: list[LayoutInfo]
    vbo: moderngl.Buffer
    ebo: moderngl.Buffer | None = None
    vao: dict[str, moderngl.VertexArray] = field(default_factory=lambda: {})

@dataclass
class UVLocation:
    x: int
    y: int
    w: int
    h: int

@dataclass
class TextureBuffer:
    frame: moderngl.Texture
    uv: UVLocation

@dataclass
class ConvertedImage:
    source: bytes
    size: tuple[int, int]
    data_format: int