import numpy as np
import uuid
import moderngl
from ..common import MeshBuffer, LayoutInfo, TextureBuffer, ConvertedImage, UVLocation
from dataclasses import dataclass
from ...resources.assets.import_data import MeshData
from ..atlas import Atlas

@dataclass
class GPUHandle:
    vbo: moderngl.Buffer
    ebo: moderngl.Buffer

class GeometryUploader:
    _ctx: moderngl.Context
    _gpu_handles: dict[str, MeshBuffer] = {}

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
    def get_current_context(cls):
        cls._ctx

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx

    @classmethod
    def _process_mesh(cls, mesh_data: MeshData) -> MeshBuffer:
        arrays_to_stack: list[np.ndarray] = []
        layout: list[LayoutInfo] = []
        
        attributes = [
            ("position", mesh_data.positions),
            ("normal", mesh_data.normals),
            ("tangent", mesh_data.tangents),
            ("texcoord_0", mesh_data.texcoord_0),
            ("texcoord_1", mesh_data.texcoord_1),
            ("color", mesh_data.colors),
            ("joints", mesh_data.joints),
            ("weights", mesh_data.weights),
        ]
        
        for attr_name, buffer_info in attributes:
            if buffer_info is not None:
                arr = buffer_info.data
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                
                arrays_to_stack.append(arr)
                
                attr_layout = LayoutInfo(
                    name=attr_name,
                    component_size=buffer_info.dim_type,
                    component_type=buffer_info.data_type,
                )
                layout.append(attr_layout)
        
        if not arrays_to_stack:
            raise ValueError(f"O mesh '{mesh_data.name}' não possui atributos de vértices válidos.")

        vbo_array = np.hstack(arrays_to_stack)
        
        vbo_bytes = np.ascontiguousarray(vbo_array).tobytes()
        vbo = cls._ctx.buffer(vbo_bytes)

        ebo = None
        if mesh_data.indices is not None:
            ebo_array = mesh_data.indices.data
            ebo_bytes = np.ascontiguousarray(ebo_array).tobytes()
            ebo = cls._ctx.buffer(ebo_bytes)
            
        return MeshBuffer(vbo=vbo, ebo=ebo, layout=layout)

    @classmethod
    def upload_mesh(cls, mesh_data: MeshData) -> str:
        key = str(uuid.uuid4())

        mesh_handle = cls._process_mesh(mesh_data)

        cls._gpu_handles[key] = mesh_handle
        return key

    @classmethod
    def get_mesh(cls, key: str) -> MeshBuffer | None:
        return cls._gpu_handles.get(key, None)

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
    def bind_model(cls, shader: moderngl.Program, mesh_buffer: MeshBuffer):
        ctx_vbo = mesh_buffer.vbo
        ctx_ebo = mesh_buffer.ebo

        types, names = cls._build_layout_format(mesh_buffer.layout)
        
        vao = cls._ctx.vertex_array( # type: ignore
            shader,
            [(ctx_vbo, types, *names)],
            index_buffer=ctx_ebo,
            index_element_size=4 if ctx_ebo is not None else 0
        )
        
        return vao

class TextureUploader:
    _ctx: moderngl.Context
    _atlas_size = 1024
    _atlas_array: list[Atlas] = []
    _atlas_loc: dict[str, Atlas] = {}
    _gpu_handles: dict[str, TextureBuffer] = {}
    _format_size: dict[str, int] = {
        "RGBA": 4,
        "BGR": 3,
        "RGB": 3,
    }

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx

    @classmethod
    def get_atlas_size(cls):
        return cls._atlas_size

    # @classmethod
    # def _new_atlas(cls) -> Atlas:
    #     size = cls._atlas_size
    #     image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    #     location = cls.create_texture(image, ConvertType.IMAGE)
        
    #     if location.texture == None:
    #         raise ValueError("Localização nula para atlas.")
        
    #     atlas = Atlas(size, size, location.texture)
    #     cls._atlas_array.append(atlas)
    #     cls._atlas_loc[location.texture] = atlas
    #     return atlas

    # @classmethod
    # def _get_current_atlas(cls, width: int, height: int) -> tuple[Atlas, Rec]:
    #     for atlas in cls._atlas_array:
    #         rect = atlas.insert(width, height)
    #         if not rect == None:
    #             return atlas, rect

    #     atlas = cls._new_atlas()
    #     rect = atlas.insert(width, height)

    #     assert rect is not None, f"O novo Atlas é pequeno demais para o tamanho {width}x{height}."

    #     return atlas, rect

    # @classmethod
    # def get_atlas(cls, occupation: str) -> Atlas:
    #     return cls._atlas_loc[occupation]

    # @classmethod
    # def texture_to_bytes(cls, texture: Image.Image | np.ndarray, convert_type: ConvertType) -> tuple[bytes | Image.Image | NDArray[np.uint8], int, int, str]:
    #     if isinstance(texture, Image.Image):
    #         if convert_type == ConvertType.VIDEO:
    #             return cls._video_to_bytes(texture)
    #         elif convert_type == ConvertType.IMAGE:
    #             return cls._image_to_bytes(texture)
            
    #         raise TypeError("Tipo de conversão inválido.")
    #     else:
    #         if convert_type == ConvertType.GIF:
    #             return cls._gif_to_bytes(texture)
            
    #         raise TypeError("Tipo de conversão inválido.")

    # @staticmethod
    # def _image_to_bytes(texture: Image.Image) -> tuple[bytes, int, int, str]:
    #     texture = texture.convert("RGBA")
    #     width, height = texture.size
    #     bytes_texture = texture.tobytes()
    #     return bytes_texture, width, height, "RGBA" # type: ignore
 
    # @staticmethod
    # def _gif_to_bytes(texture: np.ndarray) -> tuple[NDArray[np.uint8], int, int, str]:
    #     height: int
    #     width: int
    #     height, width = texture.shape[:2]

    #     if texture.shape[2] == 3:
    #         image_format: str = "RGB" # type: ignore
    #     else:
    #         image_format: str = "RGBA" # type: ignore

    #     texture = np.ascontiguousarray(texture)

    #     return texture, width, height, image_format # type: ignore

    # @staticmethod
    # def _video_to_bytes(texture: Image.Image) -> tuple[Image.Image, int, int, str]:
    #     height: int
    #     width: int
    #     height, width = texture.shape[:2] # type: ignore
    #     array_texture = np.ascontiguousarray(texture)
    #     return array_texture, width, height, "BGR" # type: ignore

    # @classmethod
    # def create_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> list[UVLocation]:
    #     uv_list: list[UVLocation] = []
    #     for i, frame in enumerate(frames):
    #         if len(location) == 0:
    #             loc = UVLocation()
    #         else:
    #             loc = location[i]
                
    #         uv = cls.create_texture_atlas(frame, convert_type, loc)
    #         uv_list.append(uv)

    #     return uv_list

    # @classmethod
    # def update_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> None:
    #     for i, frame in enumerate(frames):
    #         cls.update_texture_atlas(frame, convert_type, location[i])

    # @classmethod
    # def delete_texture_atlas_list(cls, location: list[UVLocation]) -> None:
    #     for loc in location:
    #         cls.delete_texture_atlas(loc)

    # @classmethod
    # def create_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation) -> UVLocation:
    #     image, width, height, _ = cls.texture_to_bytes(texture, convert_type)

    #     if not location.texture == None:
    #         key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)
    #         atlas = cls.get_atlas(location.texture)

    #         if not atlas.used_rects.get(key) == None:
    #             if not width == location.uv.w or not height == location.uv.h:
    #                 raise ValueError("Tamanhos não batem.")
    #             cls.update_texture_atlas(texture, convert_type, location)
    #             return location
            
    #         raise ValueError("Localização não existe em atlas.")

    #     current_atlas, rect = cls._get_current_atlas(width, height)
    #     cls._gpu_handles[current_atlas.occupation].write(image, viewport=(rect.x, rect.y, rect.w, rect.h))

    #     return UVLocation(current_atlas.occupation, rect)

    # @classmethod
    # def update_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation) -> UVLocation:
    #     image, _, _, _ = cls.texture_to_bytes(texture, convert_type)
        
    #     if location.texture == None:
    #         raise ValueError("Localização não pode ser nula.")
        
    #     uv: Rec = location.uv
    #     cls._gpu_handles[location.texture].write(image, viewport=(uv.x, uv.y, uv.w, uv.h))

    #     return location

    # @classmethod
    # def delete_texture_atlas(cls, location: UVLocation) -> None:
    #     key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)

    #     if location.texture == None:
    #         raise ValueError("Localização não pode ser nula.")
    #     atlas: Atlas = cls.get_atlas(location.texture)
    #     if not atlas.used_rects.get(key) == None:
    #         atlas.remove(location.uv)

    #         if len(atlas.used_rects) == 0 and len(cls._atlas_array) >= 2:
    #             cls.delete_texture(atlas.occupation)
    #             del cls._atlas_loc[atlas.occupation]
    #             cls._atlas_array.remove(atlas)

    
    # @classmethod
    # def update_texture(cls, occupation: str, texture: Image.Image, convert_type: ConvertType) -> UVLocation:
    #     if occupation in cls._gpu_handles:
    #         image, width, height, _ = cls.texture_to_bytes(texture, convert_type)
    #         cls._gpu_handles[occupation].write(image, viewport=(0, 0, width, height))
    #         return UVLocation(occupation, Rec(x=0, y=0, w=width, h=height))

    #     raise KeyError("Ocupação inválida.")
    

    @classmethod
    def upload_texture(cls, texture: ConvertedImage) -> str:
        key = str(uuid.uuid4())

        width, height = texture.size

        ctx_texture = cls._ctx.texture((width, height), texture.data_format, texture.source)
        ctx_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        # ctx_texture.build_mipmaps()
        handle = TextureBuffer(
            ctx_texture,
            UVLocation(0, 0, width, height)
        )

        cls._gpu_handles[key] = handle
        return key
    
    @classmethod
    def delete_texture(cls, key: str) -> None:
        if key in cls._gpu_handles:
            frame = cls._gpu_handles[key]
            frame.frame.release()
            del cls._gpu_handles[key]

    @classmethod
    def get_texture_buffer(cls, key: str) -> TextureBuffer | None:
        return cls._gpu_handles.get(key, None)

    @classmethod
    def get_texture(cls, key: str) -> moderngl.Texture | None:
        buffer = cls._gpu_handles.get(key, None)
        if buffer is None:
            return
        
        return buffer.frame

# @classmethod
#     def create_fbo(cls, size: tuple[int, int], depth: bool=False, components: int=4) -> FrameBuffer:
#         fbo_texture = cls._ctx.texture(size, components)

#         fbo_depth = None
#         if depth:
#             fbo_depth = cls._ctx.depth_texture(size)
#             # fbo_depth = cls._ctx.depth_renderbuffer(size)

#         fbo = cls._ctx.framebuffer(color_attachments=[fbo_texture], depth_attachment=fbo_depth)

#         frame = FrameBuffer(
#             texture=fbo_texture,
#             buffer=fbo,
#             components=components
#         )

#         return frame
