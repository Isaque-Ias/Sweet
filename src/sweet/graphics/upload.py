from __future__ import annotations
import uuid
import numpy as np
from typing import Any, Optional, TYPE_CHECKING
from .common import MeshBuffer, LayoutInfo, PrimitiveBufferDrawInfo
from .conversion import ImageConversion, ConvertedImage
from ..plataform.hal.manager import GraphicsDevice, VertexLayout
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
class GPUHandle:
    defined: bool
    key: str
    type: GPUHandleType

class UploadManager:
    _gfx_device: GraphicsDevice

    _gpu_handles: dict[str, Any] = {}
    
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
    def set_graphics_device(cls, gfx_device: GraphicsDevice):
        cls._gfx_device = gfx_device

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
    def _process_mesh(cls, mesh_data: MeshData) -> MeshBuffer:
        all_vbos_to_stack: list[np.ndarray] = []
        all_ebos_to_stack: list[np.ndarray] = []
        
        current_vertex_offset = 0
        current_index_byte_offset = 0
        
        primitive_buffers: list[PrimitiveBufferDrawInfo] = []
        
        global_layout: list[LayoutInfo] = []
        layout_initialized = False

        for prim in mesh_data.primitives:
            arrays_to_stack: list[np.ndarray] = []
            layout: list[LayoutInfo] = []
            
            attributes = [
                ("position", prim.positions),
                ("normal", prim.normals),
                # ("tangent", prim.tangents),
                ("texcoord_0", prim.texcoord_0),
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
                    
                    arrays_to_stack.append(arr)
                    
                    if not layout_initialized:
                        attr_layout = LayoutInfo(
                            name=attr_name,
                            component_size=buffer_info.dim_type,
                            component_type=buffer_info.data_type,
                        )
                        layout.append(attr_layout)
            
            if not arrays_to_stack:
                continue
                
            if not layout_initialized and layout:
                global_layout = layout
                layout_initialized = True

            prim_vbo_array = np.hstack(arrays_to_stack)
            num_vertices = prim_vbo_array.shape[0]
            all_vbos_to_stack.append(prim_vbo_array)

            index_count = 0
            prim_index_byte_offset = current_index_byte_offset
            
            if prim.indices is not None:
                prim_ebo_array = prim.indices.data
                index_count = prim_ebo_array.size
                all_ebos_to_stack.append(prim_ebo_array)
                
                current_index_byte_offset += prim_ebo_array.nbytes
            
            primitive_buffers.append(PrimitiveBufferDrawInfo(
                index_count=index_count,
                vertex_count=num_vertices,
                base_vertex=current_vertex_offset,
                index_byte_offset=prim_index_byte_offset
            ))
            
            current_vertex_offset += num_vertices

        if not all_vbos_to_stack:
            raise ValueError(f"O mesh '{mesh_data.name}' não possui primitivas ou atributos válidos.")

        vbo_array = np.vstack(all_vbos_to_stack)
        vbo_bytes = np.ascontiguousarray(vbo_array).tobytes()

        vbo = cls._gfx_device.create_vertex_buffer(size=len(vbo_bytes), dynamic=False)
        vbo.upload_data(vbo_bytes)

        ebo = None
        if all_ebos_to_stack:
            ebo_array = np.concatenate(all_ebos_to_stack)
            ebo_bytes = np.ascontiguousarray(ebo_array).tobytes()
            ebo = cls._gfx_device.create_index_buffer(size=len(ebo_bytes), dynamic=False)
            ebo.upload_data(ebo_bytes)
            
        return MeshBuffer(
            vbo=vbo, 
            ebo=ebo, 
            layout=global_layout, 
            primitives=primitive_buffers
        )

    @classmethod
    def _handle_for(cls, data: Any, type: GPUHandleType) -> GPUHandle:
        key = str(uuid.uuid4())
        cls._gpu_handles[key] = data
        gpu_handle = GPUHandle(defined=True, key=key, type=type)
        return gpu_handle

    @classmethod
    def retrieve_object(cls, key: str) -> Any:
        return cls._gpu_handles.get(key)

    @classmethod
    def upload_shaders(cls, shader_data: ShaderData) -> GPUHandle:
        program = cls._gfx_device.create_shader_program(shader_data)
        gpu_handle = cls._handle_for(program, GPUHandleType.SHADER)
        return gpu_handle

    @classmethod
    def upload_mesh(cls, mesh_data: MeshData) -> GPUHandle:
        processed_mesh = cls._process_mesh(mesh_data)
        gpu_handle = cls._handle_for(processed_mesh, GPUHandleType.MESH)
        return gpu_handle

    @classmethod
    def bind_primitive(
        cls, 
        mesh_key: str, 
        primitive_index: int,
        shader: Any
    ) -> Optional[VertexLayout]:
        mesh_buffer = cls._gpu_handles.get(mesh_key, None)
        if mesh_buffer is None:
            return None
        
        prim_info = mesh_buffer.primitives[primitive_index]
        
        layout_format, attr_names = cls._build_layout_format(mesh_buffer.layout)

        vertex_layout = cls._gfx_device.create_vertex_layout_primitive(
            shader=shader,
            vertex_buffer=mesh_buffer.vbo,
            layout_format=layout_format,
            attributes=attr_names,
            index_buffer=mesh_buffer.ebo,
            base_vertex=prim_info.base_vertex,
            index_byte_offset=prim_info.index_byte_offset
        )

        return vertex_layout

    @classmethod
    def bind_mesh(cls, mesh_key: str, shader: Any) -> Optional[VertexLayout]:
        mesh_buffer = cls.retrieve_object(mesh_key)
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
    def upload_texture(cls, texture: ConvertedImage) -> GPUHandle:
        device_texture = cls._gfx_device.create_texture2d(*texture.size, texture.data_format)
        device_texture.upload_pixels(texture.source, *texture.size)
        gpu_handle = cls._handle_for(device_texture, GPUHandleType.TEXTURE2D)
        return gpu_handle

    @classmethod
    def upload_texture_data(cls, texture: TextureData) -> GPUHandle:
        converted_image = ImageConversion.convert_moderngl(texture)
        device_texture = cls._gfx_device.create_texture2d(*converted_image.size, converted_image.data_format)
        device_texture.upload_pixels(converted_image.source, *converted_image.size)
        gpu_handle = cls._handle_for(device_texture, GPUHandleType.TEXTURE2D)
        return gpu_handle