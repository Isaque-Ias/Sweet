from __future__ import annotations
from collections import defaultdict
import uuid
import numpy as np
from typing import Any, Optional, TYPE_CHECKING, NamedTuple
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

class GPUVolumeSource(NamedTuple):
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

class _FogBufferHeaderCStruct(ctypes.Structure):
    _fields_ = [
        ("u_VolumeCount", ctypes.c_uint32),
        ("_pad0", ctypes.c_uint32),
        ("_pad1", ctypes.c_uint32),
        ("_pad2", ctypes.c_uint32),
    ]

class _FogVolumeCStruct(ctypes.Structure):
    _fields_ = [
        ("inv_transform", ctypes.c_float * 16),
        ("color", ctypes.c_float * 4),
        ("parameters", ctypes.c_float * 4),
        ("cloud_params", ctypes.c_float * 4),  # x: detailScale, y: animSpeed, z: softEdge, w: unused
        ("type", ctypes.c_uint32),
        ("pad0", ctypes.c_uint32),
        ("pad1", ctypes.c_uint32),
        ("pad2", ctypes.c_uint32),
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

    def update_data(self, index: int, data: np.ndarray | bytes, offset_within_block: int = 0) -> bool:
        """In-place update of data at an existing GPU index without reallocation."""
        if index not in self.allocated:
            raise KeyError(f"Index {index} de localização na GPU é inválido")
            
        start_offset, max_size, _ = self.allocated[index]
        
        raw_bytes = data.tobytes() if isinstance(data, np.ndarray) else data
        if offset_within_block + len(raw_bytes) > max_size:
            system.problem(f"Tentativa de sobrescrever bloco GPU {index} com tamanho maior que o alocado")
            return False

        self.buffer.upload_data(raw_bytes, offset=start_offset + offset_within_block)
        return True

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
    DEFAULT_WHITE_TEXTURE: GPUTexture
    
    TEXREF_BYTE_OFFSETS = {
        "albedo": 0,
        "orm": 16,
        "specular": 32,
        "emissive": 48,
        "clearcoat": 64,
        "clearcoat_roughness": 80,
    }
    
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

        # Upload 1x1 white pixel texture fallback
        white_pixel = np.array([[[255, 255, 255, 255]]], dtype=np.uint8)
        cls.DEFAULT_WHITE_TEXTURE = cls._upload_pixel_array(white_pixel, 1, 1)

    @classmethod
    def get_bindless_buffer(cls, name: str):
        buffer = cls._interleaved_buffers.get(name, None)
        if buffer is not None:
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
    def _process_mesh(
        cls, 
        mesh_data: MeshData, 
        existing_views: Optional[dict[str, GPUView]] = None
    ) -> list[GPUSource]:
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
                ("texcoords", prim.texcoord_0),
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
                    
                    if existing_views and attr_name in existing_views:
                        target_idx = existing_views[attr_name].buffer_index
                        attr_buffer.update_data(target_idx, arr)
                        vbo_view = existing_views[attr_name]
                    else:
                        buffer_index = attr_buffer.upload_data(arr)
                        vbo_view = GPUView(buffer_index=buffer_index)

                    prim_views[attr_name] = vbo_view
                elif existing_views and attr_name in existing_views:
                    prim_views[attr_name] = existing_views[attr_name]

            if not layout_initialized and layout:
                global_layout = layout
                layout_initialized = True

            ebo_view = None
            if prim.indices is not None:
                prim_ebo_array = np.array(prim.indices.data, dtype=np.uint32)
                ebo_buffer = cls.ebo_tracker
                
                if existing_views and "indices" in existing_views:
                    target_idx = existing_views["indices"].buffer_index
                    ebo_buffer.update_data(target_idx, prim_ebo_array)
                    ebo_view = existing_views["indices"]
                else:
                    ebo_buffer_index = ebo_buffer.upload_data(prim_ebo_array)
                    ebo_view = GPUView(buffer_index=ebo_buffer_index)
            elif existing_views and "indices" in existing_views:
                ebo_view = existing_views["indices"]

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
    def upload_mesh(
        cls, 
        mesh_data: MeshData, 
        existing_mesh: Optional[GPUMeshSource] = None
    ) -> list[GPUSource]:
        existing_views = None
        if existing_mesh:
            existing_views = {
                "positions": existing_mesh.positions,
                "normals": existing_mesh.normals,
                "texcoords": existing_mesh.texcoords,
                "indices": existing_mesh.indices,
            }
            existing_views = {k: v for k, v in existing_views.items() if v is not None}

        processed_mesh = cls._process_mesh(mesh_data, existing_views=existing_views)
        return processed_mesh

    @classmethod
    def update_mesh_attribute(
        cls, 
        gpu_view: GPUView, 
        attribute_type: str, 
        data: np.ndarray
    ) -> bool:
        if attribute_type in cls._interleaved_buffers:
            tracker = cls._interleaved_buffers[attribute_type]
        elif attribute_type == "indices":
            tracker = cls.ebo_tracker
        else:
            raise ValueError(f"Atributo desconhecido: {attribute_type}")

        return tracker.update_data(gpu_view.buffer_index, data)

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
    def _upload_pixel_array(
        cls, 
        pixel_array: np.ndarray, 
        width: int, 
        height: int, 
        existing_texture: Optional[GPUTexture] = None
    ) -> GPUTexture:
        rgba = cls._pack_rgba(pixel_array)
        packed = rgba.reshape(-1, 4).view(np.uint32).reshape(-1)

        if existing_texture:
            idx = existing_texture.source.buffer_index
            cls.texture_tracker.update_data(idx, packed)
            return GPUTexture(
                source=existing_texture.source,
                format=4,
                width=width,
                height=height
            )

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
    def upload_texture(
        cls, 
        texture: Optional[TextureData], 
        cache: Optional[dict[int, GPUTexture]] = None,
        existing_texture: Optional[GPUTexture] = None
    ) -> GPUTexture:
        if texture is None:
            return cls.DEFAULT_WHITE_TEXTURE

        if cache is not None and existing_texture is None:
            cached = cache.get(id(texture))
            if cached is not None:
                return cached

        pixel_array = np.asarray(texture.source, dtype=np.uint8)
        gpu_texture = cls._upload_pixel_array(
            pixel_array, texture.width, texture.height, existing_texture=existing_texture
        )

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

        r = channel_or_default(occlusion_tex, 0, 255)
        g = channel_or_default(mr_tex, 1, 255)
        b = channel_or_default(mr_tex, 2, 0)
        a = np.full((height, width), 255, dtype=np.uint8)

        return np.stack([r, g, b, a], axis=-1), width, height

    @classmethod
    def _texref_words(cls, tex: Optional[GPUTexture]) -> list[int]:
        target = tex if tex is not None else cls.DEFAULT_WHITE_TEXTURE
        return [target.source.buffer_index, target.width * target.height, target.width, target.height]

    @classmethod
    def upload_volumes(cls, volume_configs: list[dict[str, Any]], max_capacity: int = 16) -> GPUVolumeSource:
        header = _FogBufferHeaderCStruct()
        header.u_VolumeCount = len(volume_configs)

        packed_bytes = bytearray()
        packed_bytes.extend(bytes(header))

        for config in volume_configs:
            vol = _FogVolumeCStruct()
            
            inv_matrix = config.get("inv_transform", np.identity(4, dtype=np.float32))
            vol.inv_transform = (ctypes.c_float * 16)(*inv_matrix.flatten())
            
            color = config.get("color", (1.0, 1.0, 1.0, 0.1))
            vol.color = (ctypes.c_float * 4)(*color)
            
            phase_g = float(config.get("phase_g", 0.0))
            height_falloff = float(config.get("height_falloff", 0.1))
            ground_level = float(config.get("ground_level", 0.0))
            absorption = float(config.get("absorption", 0.01))
            vol.parameters = (ctypes.c_float * 4)(phase_g, height_falloff, ground_level, absorption)
            
            vol.type = int(config.get("type", 0))
            vol.pad0 = 0
            vol.pad1 = 0
            vol.pad2 = 0

            packed_bytes.extend(bytes(vol))

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
        target_gpu_material: Optional[GPUMaterial] = None,
    ) -> GPUMaterial:
        pbr = material.pbr_characteristics
        structural = material.structural_parameters

        albedo_binding = pbr.base_color_texture
        albedo_tex = (
            cls.upload_texture(albedo_binding.texture, texture_cache)
            if albedo_binding and albedo_binding.texture
            else cls.DEFAULT_WHITE_TEXTURE
        )

        occlusion_tex = (
            structural.occlusion.binding.texture
            if structural.occlusion and structural.occlusion.binding else None
        )
        mr_binding = pbr.metallic_roughness_texture
        mr_tex = mr_binding.texture if mr_binding else None

        orm_gpu: GPUTexture = cls.DEFAULT_WHITE_TEXTURE
        orm_key = (id(occlusion_tex) if occlusion_tex else None, id(mr_tex) if mr_tex else None)
        if orm_key != (None, None):
            cached_orm = orm_cache.get(orm_key)
            if cached_orm is not None:
                orm_gpu = cached_orm
            else:
                built = cls._build_orm_array(occlusion_tex, mr_tex)
                if built is not None:
                    pixel_array, width, height = built
                    orm_gpu = cls._upload_pixel_array(pixel_array, width, height)
                    orm_cache[orm_key] = orm_gpu

        specular_binding = pbr.specular_texture
        specular_tex = (
            cls.upload_texture(specular_binding.texture, texture_cache)
            if specular_binding and specular_binding.texture else cls.DEFAULT_WHITE_TEXTURE
        )

        emissive_binding = structural.emissive.texture if structural.emissive else None
        emissive_tex = (
            cls.upload_texture(emissive_binding.texture, texture_cache)
            if emissive_binding and emissive_binding.texture else cls.DEFAULT_WHITE_TEXTURE
        )
        emissive_factor = structural.emissive.factor if structural.emissive else [0.0, 0.0, 0.0]

        clearcoat_binding = getattr(pbr, "clearcoat_texture", None)
        clearcoat_tex = (
            cls.upload_texture(clearcoat_binding.texture, texture_cache)
            if clearcoat_binding and clearcoat_binding.texture else cls.DEFAULT_WHITE_TEXTURE
        )
        clearcoat_roughness_binding = getattr(pbr, "clearcoat_roughness_texture", None)
        clearcoat_roughness_tex = (
            cls.upload_texture(clearcoat_roughness_binding.texture, texture_cache)
            if clearcoat_roughness_binding and clearcoat_roughness_binding.texture else cls.DEFAULT_WHITE_TEXTURE
        )

        clearcoat_factor = getattr(pbr, "clearcoat_factor", 0.0)
        clearcoat_roughness_factor = getattr(pbr, "clearcoat_roughness_factor", 0.0)

        texref_words = np.array(
            cls._texref_words(albedo_tex) + 
            cls._texref_words(orm_gpu) +
            cls._texref_words(specular_tex) + 
            cls._texref_words(emissive_tex) +
            cls._texref_words(clearcoat_tex) +
            cls._texref_words(clearcoat_roughness_tex),
            dtype=np.uint32
        )

        occlusion_strength = structural.occlusion.scalar_modifier if structural.occlusion else 1.0
        specular_factor = getattr(pbr, "specular_factor", 1.0)
        specular_color_factor = getattr(pbr, "specular_color_factor", [1.0, 1.0, 1.0])
        
        # Extract base_color_factor (albedo factor)
        albedo_factor = getattr(pbr, "base_color_factor", [1.0, 1.0, 1.0, 1.0])

        factor_words = np.array(
            [pbr.metallic_factor, pbr.roughness_factor, occlusion_strength, specular_factor],
            dtype=np.float32
        )
        emissive_words = np.array([*emissive_factor[:3], 0.0], dtype=np.float32)
        specular_color_words = np.array([*specular_color_factor[:3], 0.0], dtype=np.float32)
        clearcoat_words = np.array([clearcoat_factor, clearcoat_roughness_factor, 0.0, 0.0], dtype=np.float32)
        
        # Pack RGBA albedo factor words (byte offset 160)
        albedo_factor_words = np.array(albedo_factor[:4], dtype=np.float32)

        payload = (
            texref_words.tobytes() + 
            factor_words.tobytes() +
            emissive_words.tobytes() + 
            specular_color_words.tobytes() +
            clearcoat_words.tobytes() +
            albedo_factor_words.tobytes()
        )

        buffer_tracker = cls._interleaved_buffers["materials"]
        if target_gpu_material:
            idx = target_gpu_material.id.buffer_index
            buffer_tracker.update_data(idx, payload)
            return target_gpu_material

        idx = buffer_tracker.upload_data(payload)
        return GPUMaterial(GPUView(idx))

    @classmethod
    def substitute_material_texture(
        cls,
        gpu_material: GPUMaterial,
        slot_name: str,
        new_texture: GPUTexture | None,
    ) -> bool:
        if slot_name not in cls.TEXREF_BYTE_OFFSETS:
            raise ValueError(f"Slot de textura inválido: {slot_name}")

        offset = cls.TEXREF_BYTE_OFFSETS[slot_name]
        words = np.array(cls._texref_words(new_texture), dtype=np.uint32)
        
        tracker = cls._interleaved_buffers["materials"]
        return tracker.update_data(gpu_material.id.buffer_index, words.tobytes(), offset_within_block=offset)

    @classmethod
    def update_material_factors(
        cls,
        gpu_material: GPUMaterial,
        metallic: Optional[float] = None,
        roughness: Optional[float] = None,
        occlusion_strength: Optional[float] = None,
        specular_factor: Optional[float] = None,
        emissive_factor: Optional[list[float]] = None,
        albedo_factor: Optional[list[float]] = None,
        clearcoat_factor: Optional[float] = None,
        clearcoat_roughness_factor: Optional[float] = None,
    ) -> bool:
        tracker = cls._interleaved_buffers["materials"]
        mat_idx = gpu_material.id.buffer_index

        if any(v is not None for v in [metallic, roughness, occlusion_strength, specular_factor]):
            raw = tracker.read_data(mat_idx)[96:112]
            current = list(np.frombuffer(raw, dtype=np.float32))

            if metallic is not None: current[0] = metallic
            if roughness is not None: current[1] = roughness
            if occlusion_strength is not None: current[2] = occlusion_strength
            if specular_factor is not None: current[3] = specular_factor

            updated_bytes = np.array(current, dtype=np.float32).tobytes()
            tracker.update_data(mat_idx, updated_bytes, offset_within_block=96)

        if emissive_factor is not None:
            arr = np.array([*emissive_factor[:3], 0.0], dtype=np.float32).tobytes()
            tracker.update_data(mat_idx, arr, offset_within_block=112)

        if any(v is not None for v in [clearcoat_factor, clearcoat_roughness_factor]):
            raw = tracker.read_data(mat_idx)[144:160]
            current = list(np.frombuffer(raw, dtype=np.float32))

            if clearcoat_factor is not None: current[0] = clearcoat_factor
            if clearcoat_roughness_factor is not None: current[1] = clearcoat_roughness_factor

            updated_bytes = np.array(current, dtype=np.float32).tobytes()
            tracker.update_data(mat_idx, updated_bytes, offset_within_block=144)

        if albedo_factor is not None:
            arr = np.array(albedo_factor[:4], dtype=np.float32).tobytes()
            tracker.update_data(mat_idx, arr, offset_within_block=160)

        return True

    @classmethod
    def upload_materials(cls, materials: dict[int, MaterialData]) -> dict[int, GPUMaterial]:
        texture_cache: dict[int, GPUTexture] = {}
        orm_cache: dict[tuple[Optional[int], Optional[int]], GPUTexture] = {}
        gpu_materials: dict[int, GPUMaterial] = {}

        for key, material in materials.items():
            gpu_material = cls.upload_material(material, texture_cache, orm_cache)
            if gpu_material is not None: # type: ignore
                gpu_materials[key] = gpu_material

        return gpu_materials