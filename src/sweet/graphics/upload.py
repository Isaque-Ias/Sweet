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
import ctypes
from PIL import Image
if TYPE_CHECKING:
    from ..resources.assets.import_data import MeshData, TextureData, ShaderData, MaterialData

class GPUHandleType(Enum):
    SHADER = auto()
    MESH = auto()
    TEXTURE2D = auto()
    TEXTURE3D = auto()
    VOLUME = auto()

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
class GPUVolumeSource:
    volume_view: GPUView
    volume_count: int

@dataclass
class GPUTexture:
    source: GPUView
    format: int
    width: int
    height: int

@dataclass
class GPUMaterial:
    id: GPUView

@dataclass
class GPUHandle:
    defined: bool
    key: str
    type: GPUHandleType

class _FogVolumeCStruct(ctypes.Structure):
    _fields_ = [
        ("invWorldMatrix", ctypes.c_float * 16),
        ("boundsMin", ctypes.c_float * 3),
        ("densityScale", ctypes.c_float),
        ("boundsMax", ctypes.c_float * 3),
        ("absorption", ctypes.c_float),
        ("scatteringColor", ctypes.c_float * 4),
        ("noiseHandle", ctypes.c_uint32 * 2),
        ("_pad", ctypes.c_uint32 * 2),
    ]

class _FogBufferHeaderCStruct(ctypes.Structure):
    _fields_ = [
        ("u_FogVolumeCount", ctypes.c_uint32),
        ("_pad", ctypes.c_uint32 * 3),
    ]

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
            "texcoords": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb)),
            "materials": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(1)),
            "volumes": GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb))
        }
        cls.texture_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_texture_buffer(base_size_mb * 4))
        cls.ebo_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(base_size_mb * 2))
        cls.range_tracker = GPUMemoryTracker(cls._gfx_device.create_bindless_storage_buffer(1))

    @classmethod
    def get_bindless_buffer(cls, name: str):
        buffer = cls._interleaved_buffers.get(name, None)
        if not buffer is None:
            return buffer
        if name == "textures":
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
    def _pack_rgba(cls, pixel_array: np.ndarray) -> np.ndarray:
        if pixel_array.ndim == 2:
            pixel_array = pixel_array[..., None]
        channels = pixel_array.shape[-1]
        if channels == 1:
            pixel_array = np.repeat(pixel_array, 3, axis=-1)
            channels = 3
        if channels == 3:
            h, w, _ = pixel_array.shape
            alpha = np.full((h, w, 1), 255, dtype=np.uint8)
            pixel_array = np.concatenate([pixel_array, alpha], axis=-1)
        elif channels != 4:
            raise ValueError(f"Formato de textura inesperado com {channels} canais")
        return np.ascontiguousarray(pixel_array, dtype=np.uint8)

    @classmethod
    def _upload_pixel_array(cls, pixel_array: np.ndarray, width: int, height: int) -> GPUTexture:
        rgba = cls._pack_rgba(pixel_array)
        packed = rgba.reshape(-1, 4).view(np.uint32).reshape(-1)

        idx = cls.texture_tracker.upload_data(packed)
        byte_offset, _ = cls.texture_tracker.get_offset_size(idx)
        assert byte_offset % 4 == 0, f"Texture byte offset {byte_offset} not 4-byte aligned"

        return GPUTexture(
            source=GPUView(buffer_index=byte_offset // 4),
            format=4,
            width=width,
            height=height
        )

    @classmethod
    def upload_texture(cls, texture: TextureData, cache: Optional[dict[int, GPUTexture]] = None) -> GPUTexture:
        if cache is not None:
            cached = cache.get(id(texture))
            if cached is not None:
                return cached

        pixel_array = np.asarray(texture.source, dtype=np.uint8)
        gpu_texture = cls._upload_pixel_array(pixel_array, texture.width, texture.height)

        if cache is not None:
            cache[id(texture)] = gpu_texture
        return gpu_texture

    @classmethod
    def _build_orm_array(
        cls, occlusion_tex: Optional[TextureData], mr_tex: Optional[TextureData]
    ) -> Optional[tuple[np.ndarray, int, int]]:
        if occlusion_tex is None and mr_tex is None:
            return None

        ref_tex = mr_tex or occlusion_tex
        width, height = ref_tex.width, ref_tex.height # type: ignore

        def channel_or_default(tex: Optional[TextureData], channel: int, default: int) -> np.ndarray:
            if tex is None:
                return np.full((height, width), default, dtype=np.uint8)
            arr = np.asarray(tex.source, dtype=np.uint8)
            if arr.ndim == 2:
                arr = arr[..., None]
            if arr.shape[-1] <= channel:
                return np.full((height, width), default, dtype=np.uint8)
            chan = arr[..., channel]
            if chan.shape != (height, width):
                chan = np.array(Image.fromarray(chan).resize((width, height), Image.NEAREST)) # type: ignore
            return chan

        r = channel_or_default(occlusion_tex, 0, 255)  # AO
        g = channel_or_default(mr_tex, 1, 255)          # roughness (glTF: G channel)
        b = channel_or_default(mr_tex, 2, 0)            # metalness (glTF: B channel)
        a = np.full((height, width), 255, dtype=np.uint8)

        return np.stack([r, g, b, a], axis=-1), width, height

    @classmethod
    def _texref_words(cls, tex: Optional[GPUTexture]) -> list[int]:
        if tex is None:
            return [0, 0, 0, 0]  # count=0 => shader's hasTexture() returns false
        return [tex.source.buffer_index, tex.width * tex.height, tex.width, tex.height]

    @classmethod
    def upload_volumes(cls, volume_configs: list[dict[str, Any]], max_capacity: int = 16) -> GPUVolumeSource:
        header = _FogBufferHeaderCStruct()
        header.u_FogVolumeCount = len(volume_configs)

        packed_bytes = bytearray()
        packed_bytes.extend(bytes(header))

        for config in volume_configs:
            vol = _FogVolumeCStruct()
            
            inv_matrix = config.get("invWorldMatrix", np.identity(4, dtype=np.float32))
            vol.invWorldMatrix = (ctypes.c_float * 16)(*inv_matrix.flatten())
            
            bounds_min = config.get("boundsMin", (-0.5, -0.5, -0.5))
            vol.boundsMin = (ctypes.c_float * 3)(*bounds_min)
            vol.densityScale = float(config.get("densityScale", 1.0))
            
            bounds_max = config.get("boundsMax", (0.5, 0.5, 0.5))
            vol.boundsMax = (ctypes.c_float * 3)(*bounds_max)
            vol.absorption = float(config.get("absorption", 0.1))
            
            scattering = config.get("scatteringColor", (1.0, 1.0, 1.0, 1.0))
            vol.scatteringColor = (ctypes.c_float * 4)(*scattering)
            
            noise_handle = config.get("noiseHandle", (0, 0))
            vol.noiseHandle = (ctypes.c_uint32 * 2)(*noise_handle)

            packed_bytes.extend(bytes(vol))

        # Pad remaining memory block to max_capacity
        empty_vol = _FogVolumeCStruct()
        for _ in range(max_capacity - len(volume_configs)):
            packed_bytes.extend(bytes(empty_vol))

        buffer_tracker = cls._interleaved_buffers["volumes"]
        idx = buffer_tracker.upload_data(bytes(packed_bytes))

        return GPUVolumeSource(
            volume_view=GPUView(buffer_index=idx),
            volume_count=len(volume_configs)
        )

    @classmethod
    def upload_material(
        cls,
        material: MaterialData,
        texture_cache: dict[int, GPUTexture],
        orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture],
    ) -> Optional[GPUMaterial]:
        pbr = material.pbr_characteristics
        structural = material.structural_parameters

        albedo_binding = pbr.base_color_texture
        if albedo_binding is None or albedo_binding.texture is None:
            system.warn(f"Material '{material.name}' sem textura base_color; upload ignorado")
            return None
        albedo_tex = cls.upload_texture(albedo_binding.texture, texture_cache)

        occlusion_tex = (
            structural.occlusion.binding.texture
            if structural.occlusion and structural.occlusion.binding else None
        )
        mr_binding = pbr.metallic_roughness_texture
        mr_tex = mr_binding.texture if mr_binding else None

        orm_gpu: Optional[GPUTexture] = None
        orm_key = (id(occlusion_tex) if occlusion_tex else None, id(mr_tex) if mr_tex else None)
        if orm_key != (None, None):
            orm_gpu = orm_cache.get(orm_key)
            if orm_gpu is None:
                built = cls._build_orm_array(occlusion_tex, mr_tex)
                if built is not None:
                    pixel_array, width, height = built
                    orm_gpu = cls._upload_pixel_array(pixel_array, width, height)
                    orm_cache[orm_key] = orm_gpu

        specular_binding = pbr.specular_texture
        specular_tex = (
            cls.upload_texture(specular_binding.texture, texture_cache)
            if specular_binding and specular_binding.texture else None
        )

        emissive_binding = structural.emissive.texture if structural.emissive else None
        emissive_tex = (
            cls.upload_texture(emissive_binding.texture, texture_cache)
            if emissive_binding and emissive_binding.texture else None
        )

        texref_words = np.array(
            cls._texref_words(albedo_tex) + cls._texref_words(orm_gpu) +
            cls._texref_words(specular_tex) + cls._texref_words(emissive_tex),
            dtype=np.uint32
        )

        occlusion_strength = structural.occlusion.scalar_modifier if structural.occlusion else 1.0
        specular_factor = getattr(pbr, "specular_factor", 1.0)
        specular_color_factor = getattr(pbr, "specular_color_factor", [1.0, 1.0, 1.0])
        emissive_factor = structural.emissive.factor if structural.emissive else [0.0, 0.0, 0.0]

        factor_words = np.array(
            [pbr.metallic_factor, pbr.roughness_factor, occlusion_strength, specular_factor],
            dtype=np.float32
        )
        emissive_words = np.array([*emissive_factor[:3], 0.0], dtype=np.float32)
        specular_color_words = np.array([*specular_color_factor[:3], 0.0], dtype=np.float32)

        payload = (
            texref_words.tobytes() + factor_words.tobytes() +
            emissive_words.tobytes() + specular_color_words.tobytes()
        )

        buffer_tracker = cls._interleaved_buffers["materials"]
        idx = buffer_tracker.upload_data(payload)
        return GPUMaterial(GPUView(idx))

    @classmethod
    def upload_materials(cls, materials: dict[int, MaterialData]) -> dict[int, GPUMaterial]:
        texture_cache: dict[int, GPUTexture] = {}
        orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture] = {}
        gpu_materials: dict[int, GPUMaterial] = {}

        for key, material in materials.items():
            gpu_material = cls.upload_material(material, texture_cache, orm_cache)
            if gpu_material is not None:
                gpu_materials[key] = gpu_material

        return gpu_materials