from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional, Union

@dataclass
class Attribute:
    name: str
    location: int
    size: int
    type_int: int
    type_name: str
    length: int

@dataclass
class DataBlock:
    name: str
    binding: int
    size: int
    members: list[Attribute]

@dataclass
class ResourceInputs:
    layout: list[Attribute]
    uniforms: list[Attribute]
    ubos: list[DataBlock]
    ssbos: list[DataBlock]

@dataclass
class ResourceOutputs:
    targets: list[Attribute]

@dataclass
class Introspection:
    inputs: ResourceInputs
    outputs: ResourceOutputs

class Texture2D(ABC):
    @abstractmethod
    def upload_pixels(self, data: Any, width: int, height: int):
        pass

    @abstractmethod
    def release(self):
        pass

class GPUShader(ABC):
    @abstractmethod
    def __init__(self, source: Any):
        pass

    def set_program_location(self, name: str, value: int) -> None: ...

    def get_introspection(self) -> Introspection: ...

    @abstractmethod
    def bind(self):
        pass

class GPUBuffer(ABC):
    @abstractmethod
    def __init__(self, size: int, dynamic: bool) -> None:
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        return self.size
        
    @abstractmethod
    def upload_data(self, data: Any, offset: int = 0):
        pass

    @abstractmethod
    def read_data(self, size: int = -1, offset: int = 0) -> bytes:
        pass

    @abstractmethod
    def release(self):
        pass

class ResourceType(Enum):
    UNIFORM_BUFFER = auto()
    STORAGE_BUFFER = auto()
    TEXTURE_2D = auto()
    SAMPLER = auto()

@dataclass
class BufferBinding:
    buffer: GPUBuffer
    offset: int = 0
    size: int = 0

@dataclass
class ResourceBinding:
    binding_slot: int
    resource_type: ResourceType
    resource: GPUBuffer | Texture2D | BufferBinding

class ResourceLayout(ABC):
    def __init__(self, bindings: list[tuple[int, ResourceType]]):
        self.bindings = dict(bindings)

class ResourceSet(ABC):
    @abstractmethod
    def update(self, bindings: list[ResourceBinding]) -> None:
        pass

    @abstractmethod
    def apply(self, set_index_offset: int = 0) -> None:
        pass

class RenderTarget(ABC):
    @property
    @abstractmethod
    def size(self) -> tuple[int, int]:
        pass

    @property
    @abstractmethod
    def color_textures(self) -> list[Texture2D]:
        pass

    @property
    @abstractmethod
    def depth_texture(self) -> Optional[Texture2D]:
        pass

    @property
    @abstractmethod
    def framebuffer(self) -> Any:
        pass

    @abstractmethod
    def release(self) -> None:
        pass
 

class VertexLayout(ABC):
    @abstractmethod
    def bind(self) -> None:
        pass

    @abstractmethod
    def release(self) -> None:
        pass

@dataclass
class RenderPipelineDescriptor:
    shader: GPUShader
    vertex_layout: VertexLayout
    primitive_topology: str = "triangles" # triangles, lines, points
    cull_mode: str = "back"
    depth_test_enable: bool = True
    depth_write_enable: bool = True
    blend_enabled: bool = False

class RenderPipeline(ABC):
    @abstractmethod
    def __init__(self, descriptor: RenderPipelineDescriptor):
        pass

    @abstractmethod
    def apply_state(self):
        pass

class CommandBuffer(ABC):
    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def begin_render_pass(self, target: RenderTarget, viewport: Optional[tuple[int, int, int, int]] = None, clear_color: tuple[float, float, float] = (0.1, 0.2, 0.3)) -> None: ...

    @abstractmethod
    def set_pipeline(self, pipeline: RenderPipeline) -> None: ...

    @abstractmethod
    def set_resource_set(self, set_index: int, resource_set: ResourceSet) -> None: ...

    @abstractmethod
    def set_vertex_buffer(self, slot: int, buffer: GPUBuffer, offset: int = 0) -> None: ...

    @abstractmethod
    def set_index_buffer(self, buffer: GPUBuffer, index_type: str = "uint32", offset: int = 0) -> None: ...

    @abstractmethod
    def use_texture(self, src_texture: Texture2D, location: int): ...

    @abstractmethod
    def use_target_texture(self, src_render_target: RenderTarget, src_attachment: int, location: int): ...

    @abstractmethod
    def set_uniform_value(self, uniform: str, value: Any): ...

    @abstractmethod
    def draw(self, vertex_count: int, instance_count: int = 1, first_vertex: int = 0, first_instance: int = 0) -> None: ...

    @abstractmethod
    def redirect(self, dst_target: RenderTarget, src_attachment: int | str, dst_attachment: int | str) -> None: ...

    @abstractmethod
    def draw_indexed(self, index_count: int, instance_count: int = 1, first_index: int = 0, base_vertex: int = 0, first_instance: int = 0) -> None: ...

    @abstractmethod
    def end_render_pass(self) -> None: ...

    @abstractmethod
    def end(self) -> None: ...

class GraphicsDevice(ABC):
    def __init__(self, hal: str):
        self._initialized = False
        self.hal: str = hal
        GraphicsDeviceManager.add_device(self, hal)

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def blit_texture_to_target(
        self, 
        src_target: RenderTarget, 
        dst_target: RenderTarget, 
        src_attachment: Union[int, str] = 0,
        dst_attachment: Union[int, str] = 0,
        src_viewport: Optional[tuple[int, int, int, int]] = None,
        dst_viewport: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        pass

    @abstractmethod
    def create_mrt_framebuffer(self, width: int, height: int, color_formats: list[int], has_depth: bool = True) -> RenderTarget:
        pass

    @abstractmethod
    def create_framebuffer(self, width: int, height: int) -> RenderTarget:
        pass
    
    @abstractmethod
    def create_shader_program(self, program: Any) -> GPUShader:
        pass
    
    @abstractmethod
    def create_vertex_buffer(self, size: int, dynamic: bool = False) -> GPUBuffer:
        pass

    @abstractmethod
    def create_index_buffer(self, size: int, dynamic: bool = False) -> GPUBuffer:
        pass

    @abstractmethod
    def create_uniform_buffer(self, size: int) -> GPUBuffer:
        pass

    @abstractmethod
    def create_texture2d(self, width: int, height: int, format: int) -> Texture2D:
        pass

    @abstractmethod
    def create_bindless_storage_buffer(self, size_mb: int) -> GPUBuffer:
        pass

    @abstractmethod
    def create_bindless_texture_buffer(self, size_mb: int) -> GPUBuffer:
        pass

    @abstractmethod
    def create_vertex_layout_primitive(
            self,
            shader: Any,
            vertex_buffer: GPUBuffer,
            layout_format: str,
            attributes: list[str],
            base_vertex: int,
            index_byte_offset: int,
            index_buffer: Optional[GPUBuffer] = None
        ) -> VertexLayout:
        pass

    @abstractmethod
    def create_vertex_layout(
        self,
        shader: Any,
        vertex_buffer: Optional[GPUBuffer] = None,
        layout_format: Optional[str] = None,
        attributes: Optional[list[str]] = None,
        index_buffer: Optional[GPUBuffer] = None,
    ) -> VertexLayout:
        pass

    @abstractmethod
    def create_resource_layout(self, bindings: list[tuple[int, ResourceType]]) -> ResourceLayout:
        pass

    @abstractmethod
    def create_resource_set(self, layout: ResourceLayout) -> ResourceSet:
        pass

    @abstractmethod
    def create_render_pipeline(self, descriptor: RenderPipelineDescriptor) -> RenderPipeline:
        pass

    @abstractmethod
    def create_command_buffer(self) -> CommandBuffer:
        pass

    @abstractmethod
    def submit(self, command_buffers: list[CommandBuffer]) -> None:
        pass

    @abstractmethod
    def shutdown(self):
        pass

class GraphicsDeviceManager:
    _devices: dict[str, GraphicsDevice] = {}

    @classmethod
    def query_devices(cls, api: str) -> GraphicsDevice:
        return cls._devices[api]

    @classmethod
    def add_device(cls, device: GraphicsDevice, api: str) -> None:
        cls._devices[api] = device