from __future__ import annotations
from collections import defaultdict
import uuid
import numpy as np
from typing import Any, Optional, TYPE_CHECKING
from sweet.core import system
from .common import LayoutInfo
from ..plataform.hal.manager import GraphicsDevice, VertexLayout, GPUBuffer, GPUShader
from enum import Enum, auto
from dataclasses import dataclass
if TYPE_CHECKING:
    from ..resources.assets.import_data import MeshData, TextureData, ShaderData

class GPUHandleType(Enum):
    SHADER = auto()
    MESH = auto()
    TEXTURE2D = auto()
    TEXTURE3D = auto()

@dataclass
class GPUView:
    buffer_index: int

@dataclass
class GPUMeshSource:
    positions: GPUView | None
    normals: GPUView | None
    texcoords: GPUView | None
    indices: GPUView | None

@dataclass
class GPUSource:
    source_model: Any
    layout: list[LayoutInfo]
    bounding: list[float]

@dataclass
class GPUTexture:
    source: GPUView
    format: int
    width: int
    height: int

@dataclass
class GPUHandle:
    defined: bool
    key: str
    type: GPUHandleType

import numpy as np

class GPUMemoryTracker:
    def __init__(self, gpu_buffer: GPUBuffer):
        self.buffer = gpu_buffer
        self.total_size = gpu_buffer.size
        
        self.next_id = 0
        
        self.allocated: dict[int, tuple[int, int, int]] = {}
        
        self.free_by_start = {0: self.total_size}
        self.free_by_end = {self.total_size: 0}

    def set_buffer_size(self, size: int):
        self.total_size = size
        self.free_by_start = {0: size}
        self.free_by_end = {size: 0}

    def upload_data(self, data: np.ndarray | bytes) -> int:
        if isinstance(data, np.ndarray):
            raw_bytes = data.tobytes()
            byte_size = len(raw_bytes)
            element_count = data.size
        else:
            raw_bytes = data
            byte_size = len(data)
            element_count = byte_size // 4
        
        chosen_start = -1
        chosen_free_size = -1
        
        for start_offset, free_size in self.free_by_start.items():
            if free_size >= byte_size:
                chosen_start = start_offset
                chosen_free_size = free_size
                break
        
        if chosen_start == -1:
            system.problem("GPU Sem memória para alocamento. Fragmentação necessária")
            return -1
            
        idx = self.next_id
        self.next_id += 1
        
        del self.free_by_start[chosen_start]
        del self.free_by_end[chosen_start + chosen_free_size]
        
        self.buffer.upload_data(raw_bytes, offset=chosen_start)
        
        self.allocated[idx] = (chosen_start, byte_size, element_count)
        
        leftover_size = chosen_free_size - byte_size
        if leftover_size > 0:
            new_free_start = chosen_start + byte_size
            new_free_end = new_free_start + leftover_size

            self.free_by_start[new_free_start] = leftover_size
            self.free_by_end[new_free_end] = new_free_start

        return idx

    def remove_data(self, index: int) -> bool:
        if index not in self.allocated:
            return False

        start, size, _ = self.allocated.pop(index)
        end = start + size

        if end in self.free_by_start:
            right_size = self.free_by_start.pop(end)
            del self.free_by_end[end + right_size]
            size += right_size
            end = start + size

        if start in self.free_by_end:
            left_start = self.free_by_end.pop(start)
            left_size = self.free_by_start.pop(left_start)
            start = left_start
            size += left_size

        self.free_by_start[start] = size
        self.free_by_end[end] = start
        return True

    def read_data(self, index: int) -> bytes:
        if index not in self.allocated:
            raise KeyError(f"Index {index} de localização na GPU é inválido")
        offset, size, _ = self.allocated[index]
        
        return self.buffer.read_data(size=size, offset=offset)

    def get_range(self, index: int) -> tuple[int, int]:
        if index not in self.allocated:
            raise KeyError(f"Index {index} de localização na GPU é inválido")
        offset, size, _ = self.allocated[index]
        return (offset, offset + size)

    def get_offset_size(self, index: int) -> tuple[int, int]:
        if index not in self.allocated:
            raise KeyError(f"Index {index} de localização na GPU é inválido")
        offset, size, _ = self.allocated[index]
        return (offset, size)

    def get_glsl_range(self, index: int) -> tuple[int, int]:
        if index not in self.allocated:
            raise KeyError(f"Index {index} is invalid")
        byte_offset, _, element_count = self.allocated[index]
        element_offset = byte_offset // 4
        return (element_offset, element_count)

class UploadManager:
    _gfx_device: GraphicsDevice

    _gpu_handles: dict[GPUHandleType, dict[str, Any]] = {}
    
    _COMPONENT_MAP = {
        "BYTE": "b",
        "UNSIGNED_BYTE": "B",
        "SHORT": "s",
        "UNSIGNED_SHORT": "S",
        "UNSIGNED_INT": "I",
        "FLOAT": "f"
    }

    _TYPE_COUNTS_MAP = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16
    }
    
    @classmethod
    def initialize(cls, graphics_device: GraphicsDevice):
        cls._gfx_device = graphics_device
        base_size_mb = 32
        cls._interleaved_buffers = {
            "positions": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb)),
            "normals": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb)),
            "texcoords": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb))
        }
        cls.texture_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_texture_buffer(base_size_mb * 4))
        cls.ebo_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb * 2))
        cls.range_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(1))

    @classmethod
    def get_bindless_buffer(cls, name: str):
        buffer = cls._interleaved_buffers.get(name, None)
        if not buffer is None:
            return buffer
        if name == "texture":
            return cls.texture_tracker
        return cls.ebo_tracker

    @classmethod
    def _build_layout_format(cls, layout_list: list[LayoutInfo]) -> tuple[str, list[str]]:
        format_parts: list[str] = []
        attr_names: list[str] = []

        for attr in layout_list:
            count = cls._TYPE_COUNTS_MAP.get(attr.component_type, 1)
            
            data_char = cls._COMPONENT_MAP.get(attr.component_type, "f")
            
            format_parts.append(f"{count}{data_char}")
            attr_names.append(attr.name)

        full_format = " ".join(format_parts)
        return full_format, attr_names

    @classmethod
    def _process_mesh(cls, mesh_data: MeshData) -> list[GPUSource]:
        sources: list[GPUSource] = []
        
        global_layout: list[LayoutInfo] = []
        layout_initialized = False
        layout_data: dict[str, Any] = defaultdict(list)

        for prim in mesh_data.primitives:
            layout: list[LayoutInfo] = []
            prim_views: dict[str, GPUView] = {}
            
            attributes = [
                ("positions", prim.positions),
                ("normals", prim.normals),
                # ("tangent", prim.tangents),
                ("texcoords", prim.texcoord_0),
                # ("texcoord_1", prim.texcoord_1),
                # ("color", prim.colors),
                # ("joints", prim.joints),
                # ("weights", prim.weights),
            ]

            for attr_name, buffer_info in attributes:
                if buffer_info is not None:
                    arr = buffer_info.data
                    if arr.ndim == 1:
                        arr = arr.reshape(-1, 1)
                    
                    layout_data[attr_name].append(arr)
                    
                    if not layout_initialized:
                        attr_layout = LayoutInfo(
                            name=attr_name,
                            component_size=buffer_info.dim_type,
                            component_type=buffer_info.data_type,
                        )
                        layout.append(attr_layout)

                    attr_buffer = cls._interleaved_buffers[attr_name]
                    buffer_index = attr_buffer.upload_data(arr)
                    vbo_view = GPUView(
                        buffer_index=buffer_index
                    )
                    prim_views[attr_name] = vbo_view
                
            if not layout_initialized and layout:
                global_layout = layout
                layout_initialized = True

            ebo_view = None
            if prim.indices is not None:
                prim_ebo_array = np.array(prim.indices.data, dtype=np.uint32)

                ebo_buffer = cls.ebo_tracker
                ebo_buffer_index = ebo_buffer.upload_data(prim_ebo_array)
                ebo_view = GPUView(
                    buffer_index=ebo_buffer_index
                )

            mesh_source = GPUMeshSource(
                positions=prim_views.get("positions"),
                normals=prim_views.get("normals"),
                texcoords=prim_views.get("texcoords"),
                indices=ebo_view
            )

            source = GPUSource(
                mesh_source,
                global_layout,
                bounding=prim.aabb
            )

            sources.append(source)

        return sources

    @classmethod
    def _handle_for(cls, data: Any, type: GPUHandleType) -> GPUHandle:
        key = str(uuid.uuid4())
        cls._gpu_handles[type][key] = data
        gpu_handle = GPUHandle(defined=True, key=key, type=type)
        return gpu_handle

    @classmethod
    def retrieve(cls, type: GPUHandleType, key: str) -> Any:
        return cls._gpu_handles[type].get(key)

    @classmethod
    def retrieve_mesh(cls, key: str) -> Any:
        return cls._gpu_handles[GPUHandleType.MESH].get(key)

    @classmethod
    def upload_shaders(cls, shader_data: ShaderData) -> GPUShader:
        program = cls._gfx_device.create_shader_program(shader_data)
        return program

    @classmethod
    def upload_mesh(cls, mesh_data: MeshData) -> list[GPUSource]:
        processed_mesh = cls._process_mesh(mesh_data)
        return processed_mesh

    @classmethod
    def bind_mesh(cls, mesh_key: str, shader: Any) -> Optional[VertexLayout]:
        mesh_buffer = cls.retrieve_mesh(mesh_key)
        if mesh_buffer is None:
            return
        
        layout = cls._build_layout_format(mesh_buffer.layout)

        vertex_layout = cls._gfx_device.create_vertex_layout(
            shader=shader,
            vertex_buffer=mesh_buffer.vbo,
            layout_format=layout[0],
            attributes=layout[1],
            index_buffer=mesh_buffer.ebo
        )

        return vertex_layout

    @classmethod
    def upload_texture(cls, texture: TextureData) -> GPUTexture:
        index = cls.texture_tracker.upload_data(texture.source.tobytes())
        buffer_view = GPUView(
            buffer_index=index
        )
        texture_source = GPUTexture(
            source=buffer_view,
            format=texture.components,
            width=texture.width,
            height=texture.height
        )
        
        return texture_source