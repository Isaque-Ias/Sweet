from pathlib import Path
import json
import struct
from ..common import ConvertType, Rec, UVLocation, Sprite, Geometry
import OpenGL.GL as gl
import numpy as np
from collections import defaultdict
import uuid
from PIL import Image
from dataclasses import dataclass
from ..camera import CameraManager
from ..path_solver import solve_path
from pathlib import Path
from numpy.typing import NDArray
from ctypes import create_string_buffer
import moderngl
@dataclass
class BufferInfo:
    buffer: moderngl.Buffer
    capacity: int 

@dataclass
class Attribute:
    name: str
    location: int
    size: int
    type_name: int
    length: int

@dataclass
class DataBlock:
    name: str
    binding: int
    size: int
    members: list[Attribute]

@dataclass
class Introspection:
    geometry_layout: list[Attribute]
    instance_layout: list[Attribute]
    uniforms: list[Attribute]
    ubos: list[DataBlock]
    ssbos: list[DataBlock]


class Shader:
    def __init__(self, name:str, vertex: str, fragment: str) -> None:
        self.built = False
        self.name = name
        self.vertex = vertex
        self.fragment = fragment

    def set_introspection(self, introspection: Introspection) -> None:
        self.introspection = introspection

    def set_program(self, program: moderngl.Program):
        self.program = program

class ShaderModels:
    _ctx: moderngl.Context

    GL_TO_MODERNGL_MAPPING: dict[int, str] = {
        gl.GL_FLOAT: "1f", #type: ignore
        gl.GL_FLOAT_VEC2: "2f", #type: ignore
        gl.GL_FLOAT_VEC3: "3f", #type: ignore
        gl.GL_FLOAT_VEC4: "4f", #type: ignore
        
        gl.GL_INT: "1i", #type: ignore
        gl.GL_INT_VEC2: "2i", #type: ignore
        gl.GL_INT_VEC3: "3i", #type: ignore
        gl.GL_INT_VEC4: "4i", #type: ignore
        
        gl.GL_UNSIGNED_INT: "1u", #type: ignore
        gl.GL_UNSIGNED_INT_VEC2: "2u", #type: ignore
        gl.GL_UNSIGNED_INT_VEC3: "3u", #type: ignore
        gl.GL_UNSIGNED_INT_VEC4: "4u", #type: ignore
    }

    _models: dict[str, Geometry] = {}
    _default_models: dict[str, Geometry] = {}

    @classmethod
    def load_default(cls, name: str):
        BASE = Path(__file__).parent
        PATH = BASE.parent / "build" / "__mesh__.json"
        with open(PATH, "r") as file:
            data = json.load(file)

        if not data.get(name) is None:
            model = data[name]
            vbo = np.array(model["vbo"], np.float32)
            ebo = np.array(model["ebo"], np.uint32)
            count = model["index_count"]
            model = Geometry(vbo_data=vbo, ebo_data=ebo, index_count=count)
            cls._default_models[name] = model
            return model

    @classmethod
    def default_model(cls, shape: str) -> Geometry:
        if not cls._default_models.get(shape) is None:
            return cls._default_models[shape]

        def_attempt = cls.load_default(shape)
        if not def_attempt is None:
            return def_attempt
        
        if cls._default_models.get("__cube__") is None:
            cls.load_default("__cube__")
            
        return cls._default_models["__cube__"]
    
    @classmethod
    def get_model(cls, name: str):
        if cls._models.get(name) is None:
            return cls.default_model(name)
        return cls._models[name]

    @classmethod
    def add_model(cls, name: str, geometry: Geometry):
        cls._models[name] = geometry

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx

    @classmethod
    def get_moderngl_format(cls, gl_type: int) -> str:
        return cls.GL_TO_MODERNGL_MAPPING.get(gl_type, "1f")

    @classmethod
    def bind_model(cls, shader: moderngl.Program, geometry_layout: list[Attribute], model: Geometry):
        ctx_vbo = cls._ctx.buffer(model.vbo_data)
        ctx_ebo = cls._ctx.buffer(model.ebo_data)

        attr_types: str = ""
        attr_names: list[str] = []
        for attr in geometry_layout:
            attr_types = attr_types + cls.get_moderngl_format(attr.type_name) + " "
            attr_names.append(attr.name)
        attr_types = attr_types[:-1]

        vao = cls._ctx.vertex_array( # type: ignore
            shader,
            [(ctx_vbo, attr_types, *attr_names)],
            index_buffer=ctx_ebo,
            index_element_size=4
        )
        return vao
    
class Atlas:
    def __init__(self, width: int, height: int, occupation: str, padding: int=0) -> None:
        self.occupation = occupation
        self.width = width
        self.height = height
        self.padding = padding
        self.tex_id = -1

        initial = Rec(0, 0, width, height)
        self.free_rects: dict[tuple[int, int, int, int], Rec] = {(initial.x, initial.y, initial.w, initial.h): initial}
        self.used_rects: dict[tuple[int, int, int, int], Rec] = {}

    def insert(self, w: int, h: int) -> Rec | None:
        w += self.padding
        h += self.padding

        best = None
        best_score = float("inf")

        for r in self.free_rects.values():
            if w <= r.w and h <= r.h:
                leftover_h = abs(r.h - h)
                leftover_w = abs(r.w - w)
                short_side = min(leftover_h, leftover_w)

                if short_side < best_score:
                    best = Rec(r.x, r.y, w, h)
                    best_score = short_side

        if best is None:
            return None

        self._place(best)
        return Rec(best.x, best.y, w - self.padding, h - self.padding)

    def _place(self, rect: Rec):
        new_free: list[Rec] = []

        for free in self.free_rects.values():
            if not self._intersect(rect, free):
                new_free.append(free)
                continue

            if rect.x > free.x:
                new_free.append(Rec(free.x, free.y, rect.x - free.x, free.h))

            if rect.x + rect.w < free.x + free.w:
                new_free.append(Rec(
                    rect.x + rect.w,
                    free.y,
                    (free.x + free.w) - (rect.x + rect.w),
                    free.h
                ))

            if rect.y > free.y:
                new_free.append(Rec(free.x, free.y, free.w, rect.y - free.y))

            if rect.y + rect.h < free.y + free.h:
                new_free.append(Rec(
                    free.x,
                    rect.y + rect.h,
                    free.w,
                    (free.y + free.h) - (rect.y + rect.h)
                ))

        pruned = self._prune(new_free)
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }
        self.used_rects[(rect.x, rect.y, rect.w, rect.h)] = rect

    def _intersect(self, a: Rec, b: Rec):
        return not (
            a.x >= b.x + b.w or
            a.x + a.w <= b.x or
            a.y >= b.y + b.h or
            a.y + a.h <= b.y
        )

    def _contains(self, a: Rec, b: Rec):
        return (
            a.x <= b.x and
            a.y <= b.y and
            a.x + a.w >= b.x + b.w and
            a.y + a.h >= b.y + b.h
        )

    def _prune(self, rects: list[Rec]):
        pruned: list[Rec] = []
        for i, r in enumerate(rects):
            contained = False
            for j, other in enumerate(rects):
                if i != j and self._contains(other, r):
                    contained = True
                    break
            if not contained:
                pruned.append(r)
        return pruned
    
    def remove(self, rect: "Rec") -> bool:
        key = (rect.x, rect.y, rect.w, rect.h)

        if key not in self.used_rects:
            return False

        del self.used_rects[key]

        self.free_rects[key] = Rec(rect.x, rect.y, rect.w, rect.h)

        self._merge_free_rects()

        return True

    def _merge_free_rects(self) -> None:
        merged = True
        
        while merged:
            merged = False
            rects = list(self.free_rects.values())

            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    a = rects[i]
                    b = rects[j]

                    merged_rect = self._try_merge(a, b)
                    if merged_rect:
                        del self.free_rects[(a.x, a.y, a.w, a.h)]
                        del self.free_rects[(b.x, b.y, b.w, b.h)]

                        self.free_rects[
                            (merged_rect.x, merged_rect.y, merged_rect.w, merged_rect.h)
                        ] = merged_rect

                        merged = True
                        break
                if merged:
                    break

        pruned = self._prune(list(self.free_rects.values()))
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }

    def _try_merge(self, a: "Rec", b: "Rec") -> Rec | None:
        if a.y == b.y and a.h == b.h:
            if a.x + a.w == b.x:
                return Rec(a.x, a.y, a.w + b.w, a.h)
            if b.x + b.w == a.x:
                return Rec(b.x, b.y, a.w + b.w, a.h)

        if a.x == b.x and a.w == b.w:
            if a.y + a.h == b.y:
                return Rec(a.x, a.y, a.w, a.h + b.h)
            if b.y + b.h == a.y:
                return Rec(b.x, b.y, a.w, a.h + b.h)

        return None

class ShaderTexture:
    _ctx: moderngl.Context
    _atlas_size = 1024
    _atlas_array: list[Atlas] = []
    _atlas_loc: dict[str, Atlas] = {}
    _occupated_textures: dict[str, moderngl.Texture] = {}
    _format_size: dict[str, int] = {
        "RGBA": 4,
        "BGR": 3,
        "RGB": 3,
    }

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx

    @classmethod
    def create_fbo(cls, size: tuple[int, int], depth: bool=False) -> moderngl.Framebuffer:
        fbo_texture = cls._ctx.texture(size, 3)

        fbo_depth = None
        if depth:
            fbo_depth = cls._ctx.depth_renderbuffer(size)

        return cls._ctx.framebuffer(color_attachments=[fbo_texture], depth_attachment=fbo_depth)

    @classmethod
    def get_atlas_size(cls):
        return cls._atlas_size

    @classmethod
    def new_atlas(cls) -> Atlas:
        size = cls._atlas_size
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        location = cls.create_texture(image, ConvertType.IMAGE)
        
        if location.texture == None:
            raise ValueError("Localização nula para atlas.")
        
        atlas = Atlas(size, size, location.texture)
        cls._atlas_array.append(atlas)
        cls._atlas_loc[location.texture] = atlas
        return atlas

    @classmethod
    def get_current_atlas(cls, width: int, height: int) -> tuple[Atlas, Rec]:
        for atlas in cls._atlas_array:
            rect = atlas.insert(width, height)
            if not rect == None:
                return atlas, rect

        atlas = cls.new_atlas()
        rect = atlas.insert(width, height)

        assert rect is not None, f"O novo Atlas é pequeno demais para o tamanho {width}x{height}."

        return atlas, rect

    @classmethod
    def get_atlas(cls, occupation: str) -> Atlas:
        return cls._atlas_loc[occupation]

    @classmethod
    def texture_to_bytes(cls, texture: Image.Image | np.ndarray, convert_type: ConvertType) -> tuple[bytes | Image.Image | NDArray[np.uint8], int, int, str]:
        if isinstance(texture, Image.Image):
            if convert_type == ConvertType.VIDEO:
                return cls._video_to_bytes(texture)
            elif convert_type == ConvertType.IMAGE:
                return cls._image_to_bytes(texture)
            
            raise TypeError("Tipo de conversão inválido.")
        else:
            if convert_type == ConvertType.GIF:
                return cls._gif_to_bytes(texture)
            
            raise TypeError("Tipo de conversão inválido.")

    @staticmethod
    def _image_to_bytes(texture: Image.Image) -> tuple[bytes, int, int, str]:
        texture = texture.convert("RGBA")
        width, height = texture.size
        bytes_texture = texture.tobytes()
        return bytes_texture, width, height, "RGBA" # type: ignore
 
    @staticmethod
    def _gif_to_bytes(texture: np.ndarray) -> tuple[NDArray[np.uint8], int, int, str]:
        height: int
        width: int
        height, width = texture.shape[:2]

        if texture.shape[2] == 3:
            image_format: str = "RGB" # type: ignore
        else:
            image_format: str = "RGBA" # type: ignore

        texture = np.ascontiguousarray(texture)

        return texture, width, height, image_format # type: ignore

    @staticmethod
    def _video_to_bytes(texture: Image.Image) -> tuple[Image.Image, int, int, str]:
        height: int
        width: int
        height, width = texture.shape[:2] # type: ignore
        array_texture = np.ascontiguousarray(texture)
        return array_texture, width, height, "BGR" # type: ignore

    @classmethod
    def create_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> list[UVLocation]:
        uv_list: list[UVLocation] = []
        for i, frame in enumerate(frames):
            if len(location) == 0:
                loc = UVLocation()
            else:
                loc = location[i]
                
            uv = cls.create_texture_atlas(frame, convert_type, loc)
            uv_list.append(uv)

        return uv_list

    @classmethod
    def update_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> None:
        for i, frame in enumerate(frames):
            cls.update_texture_atlas(frame, convert_type, location[i])

    @classmethod
    def delete_texture_atlas_list(cls, location: list[UVLocation]) -> None:
        for loc in location:
            cls.delete_texture_atlas(loc)

    @classmethod
    def create_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, _ = cls.texture_to_bytes(texture, convert_type)

        if not location.texture == None:
            key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)
            atlas = cls.get_atlas(location.texture)

            if not atlas.used_rects.get(key) == None:
                if not width == location.uv.w or not height == location.uv.h:
                    raise ValueError("Tamanhos não batem.")
                cls.update_texture_atlas(texture, convert_type, location)
                return location
            
            raise ValueError("Localização não existe em atlas.")

        current_atlas, rect = cls.get_current_atlas(width, height)
        cls._occupated_textures[current_atlas.occupation].write(image, viewport=(rect.x, rect.y, rect.w, rect.h))

        return UVLocation(current_atlas.occupation, rect)

    @classmethod
    def update_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, _, _, _ = cls.texture_to_bytes(texture, convert_type)
        
        if location.texture == None:
            raise ValueError("Localização não pode ser nula.")
        
        uv: Rec = location.uv
        cls._occupated_textures[location.texture].write(image, viewport=(uv.x, uv.y, uv.w, uv.h))

        return location

    @classmethod
    def delete_texture_atlas(cls, location: UVLocation) -> None:
        key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)

        if location.texture == None:
            raise ValueError("Localização não pode ser nula.")
        atlas: Atlas = cls.get_atlas(location.texture)
        if not atlas.used_rects.get(key) == None:
            atlas.remove(location.uv)

            if len(atlas.used_rects) == 0 and len(cls._atlas_array) >= 2:
                cls.delete_texture(atlas.occupation)
                del cls._atlas_loc[atlas.occupation]
                cls._atlas_array.remove(atlas)

    @classmethod
    def create_texture(cls, texture: Image.Image, convert_type: ConvertType, occupation: str | None=None) -> UVLocation:
        if occupation == None:
            occupation = uuid.uuid4().hex
            
        if not cls._occupated_textures.get(occupation) == None:
            return cls.update_texture(occupation, texture, convert_type)
            
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)

        format_size = cls._format_size[image_format]

        ctx_texture = cls._ctx.texture((width, height), format_size, image)
        ctx_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        # ctx_texture.build_mipmaps()

        cls._occupated_textures[occupation] = ctx_texture
        return UVLocation(occupation, uv=Rec(x=0, y=0, w=width, h=height))
    
    @classmethod
    def update_texture(cls, occupation: str, texture: Image.Image, convert_type: ConvertType) -> UVLocation:
        if occupation in cls._occupated_textures:
            image, width, height, _ = cls.texture_to_bytes(texture, convert_type)
            cls._occupated_textures[occupation].write(image, viewport=(0, 0, width, height))
            return UVLocation(occupation, Rec(x=0, y=0, w=width, h=height))

        raise KeyError("Ocupação inválida.")
    
    @classmethod
    def delete_texture(cls, occupation: str) -> None:
        if occupation in cls._occupated_textures:
            cls._occupated_textures[occupation].release()
            del cls._occupated_textures[occupation]

    @classmethod
    def get_texture(cls, occupation: str) -> moderngl.Texture:
        if occupation in cls._occupated_textures:
            return cls._occupated_textures[occupation]
        raise KeyError("Textura não existe.")

class ShaderInstrospection:
    _GL_TYPE_MAPPING: dict[int, tuple[str, int]] = {
        gl.GL_FLOAT: ("float", 4), # type: ignore
        gl.GL_FLOAT_VEC2: ("vec2", 8), # type: ignore
        gl.GL_FLOAT_VEC3: ("vec3", 12), # type: ignore  # Nota: Alinha para 16 bytes em std140
        gl.GL_FLOAT_VEC4: ("vec4", 16), # type: ignore
        gl.GL_INT: ("int", 4), # type: ignore
        gl.GL_INT_VEC2: ("ivec2", 8), # type: ignore
        gl.GL_INT_VEC3: ("ivec3", 12), # type: ignore
        gl.GL_INT_VEC4: ("ivec4", 16), # type: ignore
        gl.GL_UNSIGNED_INT: ("uint", 4), # type: ignore
        gl.GL_UNSIGNED_INT_VEC2: ("uvec2", 8), # type: ignore
        gl.GL_UNSIGNED_INT_VEC3: ("uvec3", 12), # type: ignore
        gl.GL_UNSIGNED_INT_VEC4: ("uvec4", 16), # type: ignore
        gl.GL_BOOL: ("bool", 4), # type: ignore
        gl.GL_FLOAT_MAT3: ("mat3", 36), # type: ignore
        gl.GL_FLOAT_MAT4: ("mat4", 64), # type: ignore

        gl.GL_SAMPLER_2D: ("sampler2D", 4), # type: ignore
        gl.GL_SAMPLER_CUBE: ("samplerCube", 4), # type: ignore
    }

    engine_prefix = "sw_"

    @classmethod
    def get_type_info(cls, gl_type: int) -> tuple[str, int]:
        return cls._GL_TYPE_MAPPING.get(gl_type, (f"UNKNOWN_TYPE_(0x{gl_type:X})", 0)) # type: ignore

    @staticmethod
    def get_resource_name(program: int, interface_type: int, index: int) -> str:
        length = np.array([0], dtype=np.int32)
        gl.glGetProgramResourceiv(program, interface_type, index, 1, [gl.GL_NAME_LENGTH], 1, None, length) # type: ignore
        
        if length[0] <= 1:
            return ""

        name_buf = create_string_buffer(int(length[0]))
        gl.glGetProgramResourceName(program, interface_type, index, length[0], None, name_buf)
        return name_buf.value.decode('utf-8')

    @classmethod
    def create_attribute(cls, program_id: int, interface_type: int, index: int) -> Attribute:
        name = cls.get_resource_name(program_id, interface_type, index)

        props = [gl.GL_LOCATION, gl.GL_TYPE, gl.GL_ARRAY_SIZE, gl.GL_BLOCK_INDEX] # type: ignore
        
        if interface_type == gl.GL_PROGRAM_INPUT: # type: ignore
            props = [gl.GL_LOCATION, gl.GL_TYPE, gl.GL_ARRAY_SIZE] # type: ignore
            
        elif interface_type == gl.GL_BUFFER_VARIABLE: # type: ignore
            props = [gl.GL_TYPE, gl.GL_ARRAY_SIZE] # type: ignore

        num_props = len(props)
        values = np.array([0] * num_props, dtype=np.int32)
        gl.glGetProgramResourceiv(program_id, interface_type, index, num_props, props, num_props, None, values)

        location_or_binding = 0
        gl_type = 0
        length = 1
        block_index = -1

        if interface_type == gl.GL_PROGRAM_INPUT: # type: ignore
            location_or_binding = int(values[0])
            gl_type = int(values[1])
            length = int(values[2])
        elif interface_type == gl.GL_BUFFER_VARIABLE: # type: ignore
            gl_type = int(values[0])
            length = int(values[1])
        else:
            location_or_binding = int(values[0])
            gl_type = int(values[1])
            length = int(values[2])
            block_index = int(values[3])

        _, base_size = cls.get_type_info(gl_type)
        type_name = gl_type

        is_in_block = (interface_type == gl.GL_UNIFORM and block_index != -1) or (interface_type == gl.GL_BUFFER_VARIABLE) # type: ignore
        final_size = base_size * length

        if is_in_block:
            stride_props = [gl.GL_ARRAY_STRIDE, gl.GL_MATRIX_STRIDE] # type: ignore
            stride_values = np.array([0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, interface_type, index, 2, stride_props, 2, None, stride_values)
            
            array_stride = int(stride_values[0])
            matrix_stride = int(stride_values[1])

            if matrix_stride > 0:
                num_columns = 4
                if gl_type == gl.GL_FLOAT_MAT3: # type: ignore
                    num_columns = 3
                elif gl_type == gl.GL_FLOAT_MAT2: # type: ignore
                    num_columns = 2
                
                if length > 1 and array_stride > 0:
                    final_size = array_stride * length
                else:
                    final_size = matrix_stride * num_columns
            elif length > 1 and array_stride > 0:
                final_size = array_stride * length

        return Attribute(
            name=name, 
            location=location_or_binding, 
            size=final_size, 
            type_name=type_name, 
            length=length
        )

    @classmethod
    def introspect_layout(cls, program_id: int) -> tuple[list[Attribute], list[Attribute]]:
        geometry_layout: list[Attribute] = []
        instance_layout: list[Attribute] = []

        num_inputs = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_PROGRAM_INPUT, gl.GL_ACTIVE_RESOURCES, num_inputs) # type: ignore
        
        for i in range(num_inputs[0]):
            attribute = cls.create_attribute(program_id, gl.GL_PROGRAM_INPUT, i) # type: ignore
            if attribute.name[:len(cls.engine_prefix)] == cls.engine_prefix:
                geometry_layout.append(attribute)
            else:
                instance_layout.append(attribute)
        
        geometry_layout.sort(key=lambda x: x.location)
        instance_layout.sort(key=lambda x: x.location)

        return geometry_layout, instance_layout

    @classmethod
    def introspect_uniforms(cls, program_id: int) -> list[Attribute]:
        uniforms: list[Attribute] = []

        num_uniforms = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_UNIFORM, gl.GL_ACTIVE_RESOURCES, num_uniforms) # type: ignore
        
        for i in range(num_uniforms[0]):
            attribute = cls.create_attribute(program_id, gl.GL_UNIFORM, i) # type: ignore
            if attribute.location == -1:
                continue
            uniforms.append(attribute)

        uniforms.sort(key=lambda x: x.location)

        return uniforms

    @classmethod
    def introspect_ubos(cls, program_id: int) -> list[DataBlock]:
        ubos: list[DataBlock] = []

        num_ubos = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_UNIFORM_BLOCK, gl.GL_ACTIVE_RESOURCES, num_ubos) # type: ignore
        
        for i in range(num_ubos[0]):
            block_name = cls.get_resource_name(program_id, gl.GL_UNIFORM_BLOCK, i) # type: ignore
            block_values = np.array([0, 0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, gl.GL_UNIFORM_BLOCK, i, 3,  # type: ignore
                                [gl.GL_BUFFER_BINDING, gl.GL_BUFFER_DATA_SIZE, gl.GL_NUM_ACTIVE_VARIABLES], 3, None, block_values) # type: ignore
            
            binding, data_size, num_vars = block_values
            
            members: list[Attribute] = []
            if num_vars > 0:
                var_indices = np.array([0] * num_vars, dtype=np.int32)
                gl.glGetProgramResourceiv(program_id, gl.GL_UNIFORM_BLOCK, i, 1, [gl.GL_ACTIVE_VARIABLES], num_vars, None, var_indices) # type: ignore
                
                for var_idx in var_indices:
                    attribute = cls.create_attribute(program_id, gl.GL_UNIFORM, var_idx) # type: ignore
                    members.append(attribute)
                    
            ubo = DataBlock(name=block_name, binding=binding, size=data_size, members=members)
            ubos.append(ubo)

        ubos.sort(key=lambda x: x.binding)

        return ubos

    @classmethod
    def introspect_ssbos(cls, program_id: int) -> list[DataBlock]:
        ssbos: list[DataBlock] = []
        num_ssbos = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, gl.GL_ACTIVE_RESOURCES, num_ssbos) # type: ignore
        
        for i in range(num_ssbos[0]):
            block_name = cls.get_resource_name(program_id, gl.GL_SHADER_STORAGE_BLOCK, i) # type: ignore
            block_values = np.array([0, 0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, i, 3,  # type: ignore
                                [gl.GL_BUFFER_BINDING, gl.GL_BUFFER_DATA_SIZE, gl.GL_NUM_ACTIVE_VARIABLES], 3, None, block_values) # type: ignore
            
            binding, data_size, num_vars = block_values
            
            members: list[Attribute] = []
            if num_vars > 0:
                var_indices = np.array([0] * num_vars, dtype=np.int32)
                gl.glGetProgramResourceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, i, 1, [gl.GL_ACTIVE_VARIABLES], num_vars, None, var_indices) # type: ignore
                
                for var_idx in var_indices:
                    attribute = cls.create_attribute(program_id, gl.GL_BUFFER_VARIABLE, var_idx) # type: ignore
                    members.append(attribute)

            ssbo = DataBlock(name=block_name, binding=binding, size=data_size, members=members)
            ssbos.append(ssbo)
            
        ssbos.sort(key=lambda x: x.binding)

        return ssbos

    @classmethod
    def introspect_program(cls, program_id: int) -> Introspection:
        geometry_layout, instance_layout = cls.introspect_layout(program_id)
        uniforms = cls.introspect_uniforms(program_id)
        ubos = cls.introspect_ubos(program_id)
        ssbos = cls.introspect_ssbos(program_id)

        introspection = Introspection(geometry_layout=geometry_layout, instance_layout=instance_layout, uniforms=uniforms, ubos=ubos, ssbos=ssbos)
        
        return introspection

class ShaderManager:
    _ctx: moderngl.Context
    _current_program: Shader = Shader("", "", "")
    _shaders: dict[str, Shader] = {}

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx
        ShaderTexture.set_context(ctx)
        ShaderRender.set_context(ctx)
        ShaderModels.set_context(ctx)

    @classmethod
    def load_json_shaders(cls, json_path: str | Path) -> None:
        absolute_path = solve_path(json_path)
        with open(absolute_path, "r") as file:
            data = json.load(file)

        data = data.get("shaders")

        if data:
            for name, shader_info in data.items():
                vertex_path = shader_info.get("vertex")
                fragment_path = shader_info.get("fragment")
                if vertex_path and fragment_path:
                    cls.add_shader(name, vertex_path, fragment_path)

    @classmethod
    def add_shader(cls, name: str, path_vertex: str | Path, path_fragment: str | Path) -> Shader:
        absolute_vertex = solve_path(path_vertex)
        absolute_fragment = solve_path(path_fragment)
        with open(absolute_vertex, "r") as file:
            VERTEX_SHADER = file.read()
        with open(absolute_fragment, "r") as file:
            FRAGMENT_SHADER = file.read()

        cls._shaders[name] = Shader(name=name, vertex=VERTEX_SHADER, fragment=FRAGMENT_SHADER)
        cls.build_shader(cls._shaders[name])
        return cls._shaders[name]

    @classmethod
    def build_shader(cls, shader: Shader) -> None:
        if not shader.built:
            program = cls._ctx.program(vertex_shader=shader.vertex, fragment_shader=shader.fragment)
            shader.set_program(program)
            
            introspection = ShaderInstrospection.introspect_program(program.glo)
            shader.set_introspection(introspection)

            shader.built = True

    @classmethod
    def build_all_shaders(cls) -> None:
        for shader in cls._shaders.values():
            cls.build_shader(shader)

    @classmethod
    def get_shader(cls, name: str) -> Shader:
        return cls._shaders[name]

    @classmethod
    def set_shader(cls, name: str) -> None:
        shader = cls.get_shader(name)
        cls._current_program = shader
        
    @classmethod
    def get_current_shader(cls) -> Shader:
        return cls._current_program

class ShaderRender:
    _draw_calls: list[Sprite] = []
    _projections: dict[str, NDArray[np.float32]] = {}
    _viewsize: tuple[int, int, int, int] = (0, 0, 0, 0)
    _fov = 70
    built = False
    buffer_map: dict[str, dict[int, BufferInfo]] = {}
    batches: dict[str, dict[str | None, dict[str, list[Sprite]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list))) # type: ignore
    ubo_data: dict[int, dict[str, dict[str, tuple[int | float, ...] | str]]] = {}
    ssbo_data: dict[int, dict[str, dict[str, tuple[int | float, ...] | str]]] = {}

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx
        cls._instance_ssbo = cls._ctx.buffer(reserve=4 * 1024 * 1024)
        cls._camera_ubo = cls._ctx.buffer(reserve=128 + 4 + 4 + 4)
        cls._ctx.enable(moderngl.DEPTH_TEST)
        # cls._ctx.enable(moderngl.CULL_FACE)

    @classmethod
    def set_frame_buffer(cls, frame_buffer: moderngl.Framebuffer | None, depth_test: bool=True, clear_color: tuple[float, float, float, float]=(0, 0, 0, 1)):
        renderer = frame_buffer
        if renderer == None:
            renderer = cls._ctx.screen
        
        renderer.use()
        if depth_test:
            cls._ctx.enable(moderngl.DEPTH_TEST)
        else:
            cls._ctx.disable(moderngl.DEPTH_TEST)
        renderer.clear(*clear_color)

    @classmethod
    def update_projections(cls, fov: float) -> None:
        x, y, width, height = cls._ctx.screen.viewport
        cls._viewsize = x, y, width, height
        cls._fov = fov

        cls._projections["perspective"] = cls.create_perspective(
            cls._fov,
            width / height,
            0.1,
            100000.0
        )
        cls._projections["orthogonal"] = cls.create_ortho(
            -width / 100, width / 100,
            -height / 100, height / 100,
            -100,
            100
        )

    @staticmethod
    def create_perspective(fov_degrees: float, aspect_ratio: float, near: float, far: float):
        fov_radians = np.radians(fov_degrees)
        
        tan_half_fov = np.tan(fov_radians / 2.0)
        
        f = 1.0 / tan_half_fov
        
        proj = np.array([
            [f / aspect_ratio, 0.0, 0.0,                              0.0],
            [0.0,              f,   0.0,                              0.0],
            [0.0,              0.0, (far + near) / (near - far),      (2.0 * far * near) / (near - far)],
            [0.0,              0.0, -1.0,                             0.0]
        ], dtype=np.float32)
        
        return proj.T

    @staticmethod
    def create_ortho(left: float, right: float, bottom: float, top: float, near: float, far: float):
        ortho = np.array([
            [2.0 / (right - left), 0.0,                  0.0,                  -(right + left) / (right - left)],
            [0.0,                  2.0 / (top - bottom), 0.0,                  -(top + bottom) / (top - bottom)],
            [0.0,                  0.0,                  -2.0 / (far - near),  -(far + near) / (far - near)],
            [0.0,                  0.0,                  0.0,                  1.0]
        ], dtype=np.float32)
        
        return ortho.T

    @staticmethod
    def create_view_matrix(pos: tuple[float, float, float], angles: tuple[float, float, float]):
        pitch, yaw, roll = angles
        cam_x, cam_y, cam_z = pos

        cx, sx = np.cos(-pitch), np.sin(-pitch)
        cy, sy = np.cos(-yaw),   np.sin(-yaw)
        cz, sz = np.cos(-roll),  np.sin(-roll)

        Rx = np.array([[1, 0, 0, 0], [0, cx, sx, 0], [0, -sx, cx, 0], [0, 0, 0, 1]], dtype=np.float32)
        Ry = np.array([[cy, 0, -sy, 0], [0, 1, 0, 0], [sy, 0, cy, 0], [0, 0, 0, 1]], dtype=np.float32)
        Rz = np.array([[cz, sz, 0, 0], [-sz, cz, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32)

        r_view = Ry @ Rx @ Rz

        t_view = np.array([
            [1.0,     0.0,     0.0,     0.0],
            [0.0,     1.0,     0.0,     0.0],
            [0.0,     0.0,     1.0,     0.0],
            [-cam_x, -cam_y,  -cam_z,   1.0]
        ], dtype=np.float32)

        return t_view @ r_view

    @staticmethod
    def create_model_matrix(sprite: Sprite):
        x, y, z = sprite.pos
        w, h, t = sprite.scale
        pitch, yaw, roll = sprite.rotation

        t_matrix = np.array([
            [1.0,   0.0,   0.0,   0.0],
            [0.0,   1.0,   0.0,   0.0],
            [0.0,   0.0,   1.0,   0.0],
            [x, y, z, 1.0]
        ], dtype=np.float32)

        s_matrix = np.array([
            [w,   0.0, 0.0, 0.0],
            [0.0, h,   0.0, 0.0],
            [0.0, 0.0, t,   0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32)

        cx, sx = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw),   np.sin(yaw)
        cz, sz = np.cos(roll),  np.sin(roll)

        Rx = np.array([[1, 0, 0, 0], [0, cx, sx, 0], [0, -sx, cx, 0], [0, 0, 0, 1]], dtype=np.float32)
        Ry = np.array([[cy, 0, -sy, 0], [0, 1, 0, 0], [sy, 0, cy, 0], [0, 0, 0, 1]], dtype=np.float32)
        Rz = np.array([[cz, sz, 0, 0], [-sz, cz, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32)

        r_matrix = Rx @ Ry @ Rz

        return s_matrix @ r_matrix @ t_matrix
    
    @classmethod
    def add_ubo_data(cls, binding: int, name: str, data_type: str,  *value: int | float) -> None:
        if cls.ubo_data.get(binding) is None:
            cls.ubo_data[binding] = {}

        cls.ubo_data[binding][name] = {"value": value, "type": data_type}

    @classmethod
    def add_ssbo_data(cls, binding: int, name: str, data_type: str, *value: int | float) -> None:
        if cls.ssbo_data.get(binding) is None:
            cls.ssbo_data[binding] = {}

        cls.ssbo_data[binding][name] = {"value": value, "type": data_type}

    @classmethod
    def add_draw_call(cls, sprite: Sprite) -> None:
        shader = sprite.shader
        texture = sprite.texture if sprite.texture is None else sprite.texture.texture
        model = sprite.model
        cls.batches[shader][texture][model].append(sprite) # type: ignore

    @classmethod
    def render(cls) -> None:
        curr_camera = CameraManager.get_main_camera()

        if cls._viewsize != cls._ctx.screen.viewport or cls._fov != curr_camera.fov:
            cls.update_projections(curr_camera.fov)
        projection_matrix = cls._projections["perspective"]

        angle_mapping: tuple[float, float, float] = (
            np.radians(-curr_camera.angles.y),
            np.radians(curr_camera.angles.x),
            np.radians(curr_camera.angles.z)
        )
        view_matrix = cls.create_view_matrix(curr_camera.pos.unp(), angle_mapping)
        
        for shader_name, texture_dict in cls.batches.items():
            prog_info = ShaderManager.get_shader(shader_name)
            if not prog_info: continue
            program = prog_info.program

            for ubo in prog_info.introspection.ubos:
                if cls.buffer_map.get(shader_name) is None:
                    cls.buffer_map[shader_name] = {}

                if cls.buffer_map[shader_name].get(ubo.binding) is None:
                    size = ubo.size
                    cls.buffer_map[shader_name][ubo.binding] = BufferInfo(
                        buffer=cls._ctx.buffer(reserve=size),
                        capacity=size
                    )

                ubo_buffer = cls.buffer_map[shader_name][ubo.binding]

                buffer_data = bytearray()

                for member in ubo.members:
                    var_name = member.name.split(".")[-1]
                    if ubo.name == ShaderInstrospection.engine_prefix + "Camera":
                        if var_name == ShaderInstrospection.engine_prefix + "projection":
                            buffer_data.extend(projection_matrix.tobytes())
                        elif var_name == ShaderInstrospection.engine_prefix + "view":
                            buffer_data.extend(view_matrix.tobytes())
                        elif cls.ubo_data.get(ubo.binding, {}).get(var_name):
                            data_type: str = cls.ubo_data[ubo.binding][var_name]["type"] # type: ignore
                            data_value = cls.ubo_data[ubo.binding][var_name]["value"]
                            buffer_data.extend(struct.pack(data_type, *data_value))
                        continue

                    if cls.ubo_data.get(ubo.binding, {}).get(var_name):
                        data_type: str = cls.ubo_data[ubo.binding][var_name]["type"] # type: ignore
                        data_value = cls.ubo_data[ubo.binding][var_name]["value"]
                        buffer_data.extend(struct.pack(data_type, *data_value))
                
                ubo_buffer.buffer.write(buffer_data)
                ubo_buffer.buffer.bind_to_uniform_block(ubo.binding)
            
            instance_buffer = None
            instance_ssbo = None
            for ssbo in prog_info.introspection.ssbos:
                if ssbo.name == ShaderInstrospection.engine_prefix + "InstanceBuffer":
                    if cls.buffer_map.get(shader_name) is None:
                        cls.buffer_map[shader_name] = {}

                    if cls.buffer_map[shader_name].get(ssbo.binding) is None:
                        initial_size = ssbo.size
                        cls.buffer_map[shader_name][ssbo.binding] = BufferInfo(
                            buffer=cls._ctx.buffer(reserve=initial_size),
                            capacity=initial_size
                        )

                    instance_buffer = cls.buffer_map[shader_name][ssbo.binding]
                    instance_ssbo = ssbo
                    break

            for texture_name, mesh_dict in texture_dict.items():
                if not texture_name is None:
                    tex = ShaderTexture.get_texture(texture_name)
                    if tex:
                        tex.use(location=0) 

                        if ShaderInstrospection.engine_prefix + "texture" in map(lambda x: x.name, prog_info.introspection.uniforms):
                            program[ShaderInstrospection.engine_prefix + "texture"].value = 0 # type: ignore

                for mesh_name, objects in mesh_dict.items():
                    mesh = ShaderModels.get_model(mesh_name)
                    if not mesh: continue

                    if not mesh.vao:
                        mesh.vao = ShaderModels.bind_model(program, prog_info.introspection.geometry_layout, mesh)

                    if not instance_buffer is None and not instance_ssbo is None:
                        bytes_per_instance = instance_ssbo.size
                        required_size = bytes_per_instance * len(objects)

                        current_buffer = instance_buffer.buffer
                        current_capacity = instance_buffer.capacity

                        if required_size > current_capacity:
                            new_capacity = current_capacity
                            while new_capacity < required_size:
                                new_capacity *= 2
                            
                            current_buffer.release()
                            current_buffer = cls._ctx.buffer(reserve=new_capacity)
                            
                            instance_buffer.buffer = current_buffer
                            instance_buffer.capacity = new_capacity

                        buffer_data = cls.create_instance_buffer(objects, instance_ssbo)
                        instance_buffer.buffer.write(buffer_data)
                        instance_buffer.buffer.bind_to_storage_buffer(instance_ssbo.binding)

                    mesh.vao.render(mode=moderngl.TRIANGLES, instances=len(objects))

        cls.batches = defaultdict(lambda: defaultdict(lambda: defaultdict(list))) # type: ignore
        
    @classmethod
    def create_instance_buffer(cls, sprites: list[Sprite], ssbo: DataBlock) -> bytearray:
        buffer_data = bytearray()
        
        for obj in sprites:
            for member in ssbo.members:
                var_name = member.name.split(".")[-1]
                if var_name == ShaderInstrospection.engine_prefix + "model":
                    model_matrix = cls.create_model_matrix(obj)
                    buffer_data.extend(model_matrix.tobytes())
                elif var_name == ShaderInstrospection.engine_prefix + "UV":
                    if not obj.texture is None:
                        atlas_size = ShaderTexture.get_atlas_size()
                        u0 = obj.texture.uv.x / atlas_size
                        v0 = obj.texture.uv.y / atlas_size
                        us = obj.texture.uv.w / atlas_size * 0.999
                        vs = obj.texture.uv.h / atlas_size * 0.999
                        buffer_data.extend(struct.pack('4f', u0, v0, us, vs))
                elif var_name == ShaderInstrospection.engine_prefix + "color":
                    buffer_data.extend(struct.pack('4f', *obj.color))
                if cls.ubo_data.get(ssbo.binding, {}).get(var_name):
                    data_type: str = cls.ssbo_data[ssbo.binding][var_name]["type"] # type: ignore
                    data_value = cls.ssbo_data[ssbo.binding][var_name]["value"]
                    buffer_data.extend(struct.pack(data_type, *data_value))

        return buffer_data