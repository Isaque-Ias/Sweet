from ..common import Draw, ConvertType, Rec, UVLocation
import pygame as pg
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
from pathlib import Path
from math import sin, cos, radians
from sweet.camera import Camera
from typing import Callable, Sequence, Type
import uuid
from PIL import Image
from ..camera import Camera

class Atlas:
    def __init__(self, width, height, occupation, padding=0) -> None:
        self.occupation = occupation
        self.width = width
        self.height = height
        self.padding = padding

        self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        initial = Rec(0, 0, width, height)
        self.free_rects = {(initial.x, initial.y, initial.w, initial.h): initial}
        self.used_rects = {}

    def insert(self, w, h) -> "Rec":
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

    def _place(self, rect):
        new_free = []

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

    def _intersect(self, a, b):
        return not (
            a.x >= b.x + b.w or
            a.x + a.w <= b.x or
            a.y >= b.y + b.h or
            a.y + a.h <= b.y
        )

    def _contains(self, a, b):
        return (
            a.x <= b.x and
            a.y <= b.y and
            a.x + a.w >= b.x + b.w and
            a.y + a.h >= b.y + b.h
        )

    def _prune(self, rects):
        pruned = []
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

    def _try_merge(self, a: "Rec", b: "Rec") -> "Rec":
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

class ShaderHandler:
    screen_size: tuple = (800, 600)
    _shader_files = {}
    _occupated_textures: dict[int] = {}
    _current_program: str = None
    _uniform_mappings: dict[Callable] = {
        "1i": glUniform1i,
        "2i": glUniform2i,
        "3i": glUniform3i,
        "4i": glUniform4i,
        "1f": glUniform1f,
        "2f": glUniform2f,
        "3f": glUniform3f,
        "4f": glUniform4f,
        "1fv": glUniform1fv,
        "2fv": glUniform2fv,
        "3fv": glUniform3fv,
        "4fv": glUniform4fv
    }
    _atlas_array: list[Atlas] = []
    _atlas_loc: dict[Atlas] = {}
    _atlas_size = 1024
    _render_list: list = []

    _CWD = Path.cwd()
    _SHADERS = _CWD / "app" / "shaders"

    def ortho(left, right, bottom, top, near=-1, far=1):
        return np.array([
            [2/(right-left), 0, 0, -(right+left)/(right-left)],
            [0, 2/(top-bottom), 0, -(top+bottom)/(top-bottom)],
            [0, 0, -2/(far-near), -(far+near)/(far-near)],
            [0, 0, 0, 1]
        ], dtype=np.float32)

    @classmethod
    def new_atlas(cls) -> None:
        atlas = Atlas(cls._atlas_size, cls._atlas_size, uuid.uuid4().hex)
        location = cls.add_texture(atlas.image, ConvertType.IMAGE, atlas.occupation)
        atlas.tex_id = location.tex_id
        cls._atlas_array.append(atlas)
        cls._atlas_loc[location.tex_id] = atlas

    @classmethod
    def affine_transform(cls, pos: tuple, scale: tuple, angle: int, static: bool) -> np.array:
        c: float
        s: float
        c, s = cos(angle), sin(angle)

        tx: float
        ty: float
        tx = pos[0] * 2 / cls.screen_size[0]
        ty = pos[1] * 2 / cls.screen_size[1]

        if not static:
            main_cam = Camera.get_main_camera()
            cam_pos = main_cam.get_pos()
            cam_scale = main_cam.get_scale()
            cam_angle = main_cam.get_angle()
            cam_c, cam_s = cos(cam_angle), sin(cam_angle)
            tx = (pos[0] - cam_pos[0]) * 2 / cls.screen_size[0]
            ty = (pos[1] - cam_pos[1]) * 2 / cls.screen_size[1]

            cam_rotation_z = np.array([
                [ cam_c, -cam_s * (cls.screen_size[0] / cls.screen_size[1]), 0, 0],
                [ cam_s,  cam_c * (cls.screen_size[0] / cls.screen_size[1]), 0, 0],
                [ 0,  0, 1, 0],
                [ 0,  0, 0, 1]
            ], dtype=np.float32)

            cam_scaling = np.array([
                [cam_scale[1], 0, 0, 0],
                [0, cam_scale[0] * cls.screen_size[1] / cls.screen_size[0], 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)

        rotation_z = np.array([
            [ c, -s * (cls.screen_size[0] / cls.screen_size[1]), 0, 0],
            [ s,  c * (cls.screen_size[0] / cls.screen_size[1]), 0, 0],
            [ 0,  0, 1, 0],
            [ 0,  0, 0, 1]
        ], dtype=np.float32)

        scaling = np.array([
            [scale[0] * 2 / cls.screen_size[0], 0, 0, 0],
            [0, scale[1] * 2 / cls.screen_size[0], 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        translation = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [tx - 1, 1 - ty, 0, 1]
        ], dtype=np.float32)

        if static:
            return scaling @ rotation_z @ translation

        return scaling @ rotation_z @ translation @ cam_scaling @ cam_rotation_z
    
    @classmethod
    def get_uniform_func(cls, data_type: str) -> Callable:
        return cls._uniform_mappings[data_type]

    @classmethod
    def set_size(cls, size: tuple) -> None:
        cls.screen_size = size

    @classmethod
    def get_size(cls) -> tuple:
        return cls.screen_size
    
    @classmethod
    def generate_shader_programs(cls) -> None:
        cls.new_atlas()
        files: dict[str, str] = cls.get_shader_files()
        for key in files:
            vertex: str
            fragment: str
            vertex, fragment = files[key]["vertex"], files[key]["fragment"]
            cls._shader_files[key]["program"] = cls.create_shader_program(vertex, fragment)
            vao, vbo, stride = cls.create_vao(cls._shader_files[key]["layout"])
            cls._shader_files[key]["vao"] = vao
            cls._shader_files[key]["vbo"] = vbo
            cls._shader_files[key]["stride_size"] = stride

    @classmethod
    def get_shader_files(cls) -> dict[str, str]:
        return cls._shader_files

    @classmethod
    def get_shader_file(cls, name: str) -> dict[str, str]:
        return cls._shader_files[name]

    @classmethod
    def get_shader_program(cls, name: str) -> Callable:
        return cls._shader_files[name]["program"]

    @classmethod
    def set_default_file_path(cls, path: str) -> None:
        cls._SHADERS = path

    @classmethod
    def add_shader_file(cls, name: str, layout: dict) -> None:
        with open(cls._SHADERS / (name + ".vsh"), "r") as file:
            VERTEX_SHADER = file.read()
        with open(cls._SHADERS / (name + ".fsh"), "r") as file:
            FRAGMENT_SHADER = file.read()
        cls._shader_files[name] = {"vertex": VERTEX_SHADER, "fragment": FRAGMENT_SHADER}
        cls._shader_files[name]["layout"] = layout

    @staticmethod
    def create_shader_program(vertex: str, fragment: str) -> Callable:
        shader = compileProgram(
            compileShader(vertex, GL_VERTEX_SHADER),
            compileShader(fragment, GL_FRAGMENT_SHADER),
            validate=False
        )
        return shader

    @classmethod
    def init_pygame_opengl(cls, flags: int, color: tuple) -> None:
        display = cls.screen_size

        pg.display.gl_set_attribute(pg.GL_MULTISAMPLEBUFFERS, 0)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, 0)

        pg.display.gl_set_attribute(pg.GL_ALPHA_SIZE, 8)
        pg.display.set_mode(display, flags)
        pg.display.set_caption("test")

        glViewport(0, 0, display[0], display[1])
        glDisable(GL_MULTISAMPLE)
        
        glClearColor(*map(lambda x: x / 255, color))

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    def create_vao(layout: dict) -> object:
        vertices = np.array([
            -0.5, -0.5, 0.0,   1, 1, 1,    0, 0,
             0.5, -0.5, 0.0,   1, 1, 1,    1, 0,
             0.5,  0.5, 0.0,   1, 1, 1,    1, 1,
            -0.5,  0.5, 0.0,   1, 1, 1,    0, 1,
        ], dtype=np.float32)

        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)

        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        instance_vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        glBindVertexArray(vao)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        stride = 8 * vertices.itemsize

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)

        stride = sum(size for _, size in layout) * 4
        offset = 0

        MAX_SPRITES = 50000
        FLOATS_PER_INSTANCE = stride
        glBufferData(GL_ARRAY_BUFFER, MAX_SPRITES * FLOATS_PER_INSTANCE * 4, None, GL_DYNAMIC_DRAW)

        for i, (name, size) in enumerate(layout, start=3):
            glVertexAttribPointer(i, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset))
            glEnableVertexAttribArray(i)
            glVertexAttribDivisor(i, 1)

            offset += size * 4

        glBindVertexArray(0)

        return vao, instance_vbo, stride // 4

    @classmethod
    def setup_textured_quad(cls) -> list[int, int]:
        vertices = np.array([
            -0.5, -0.5, 0.0,   1, 1, 1,    0, 0,
             0.5, -0.5, 0.0,   1, 1, 1,    1, 0,
             0.5,  0.5, 0.0,   1, 1, 1,    1, 1,
            -0.5,  0.5, 0.0,   1, 1, 1,    0, 1,
        ], dtype=np.float32)

        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)

        instance_vbo = glGenBuffers(1)
        VAO = glGenVertexArrays(1)
        VBO = glGenBuffers(1)
        EBO = glGenBuffers(1)

        glBindVertexArray(VAO)

        glBindBuffer(GL_ARRAY_BUFFER, VBO)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        stride = 8 * vertices.itemsize

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        glEnableVertexAttribArray(2)

        glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)

        MAX_SPRITES = 50000
        FLOATS_PER_INSTANCE = 10
        glBufferData(GL_ARRAY_BUFFER, MAX_SPRITES * FLOATS_PER_INSTANCE * 4, None, GL_DYNAMIC_DRAW)

        stride = 10 * 4

        glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(3)
        glVertexAttribDivisor(3, 1)

        glVertexAttribPointer(4, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(4)
        glVertexAttribDivisor(4, 1)

        glVertexAttribPointer(5, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(4 * 4))
        glEnableVertexAttribArray(5)
        glVertexAttribDivisor(5, 1)

        glVertexAttribPointer(6, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6 * 4))
        glEnableVertexAttribArray(6)
        glVertexAttribDivisor(6, 1)

        glVertexAttribPointer(7, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8 * 4))
        glEnableVertexAttribArray(7)
        glVertexAttribDivisor(7, 1)

    @classmethod
    def set_shader(cls, shader: str) -> None:
        shader_program = cls.get_shader_program(shader)
        glUseProgram(shader_program)
        cls._current_program = shader_program
        cls.u_mvp_loc = glGetUniformLocation(shader_program, "u_mvp")

        shader_file = cls.get_shader_file(shader)
        cls.instance_vbo = shader_file["vbo"]
        cls.vao = shader_file["vao"]
        cls.stride_size = shader_file["stride_size"]
        
    @classmethod
    def get_current_shader(cls) -> Callable:
        return cls._current_program

    @classmethod
    def set_uniform_value(cls, uniform: str, data_type: str, *value: list) -> None:
        u = glGetUniformLocation(cls.get_current_shader(), uniform)
        func = cls.get_uniform_func(data_type)
        value = list(value)
        params = [u] + value
        func(*params)

    @classmethod
    def byte_texture(cls, texture: Draw, convert_type: ConvertType) -> Draw:
        if convert_type == ConvertType.VIDEO:
            return cls.byte_texture_vid(texture)
        elif convert_type == ConvertType.GIF:
            return cls.byte_texture_gif(texture)
        elif convert_type == ConvertType.IMAGE:
            return cls.byte_texture_img(texture)

    @staticmethod
    def byte_texture_img(texture: Draw) -> Draw:
        texture = texture.convert("RGBA")
        width, height = texture.size
        texture = texture.tobytes()
        return texture, width, height, GL_RGBA
    
    @staticmethod
    def byte_texture_gif(texture: Draw) -> Draw:
        height, width = texture.shape[:2]

        if texture.shape[2] == 3:
            image_format = GL_RGB
        else:
            image_format = GL_RGBA

        texture = np.ascontiguousarray(texture)

        return texture, width, height, image_format

    @staticmethod
    def byte_texture_vid(texture: Draw) -> Draw:
        height, width = texture.shape[:2]
        texture = np.ascontiguousarray(texture)
        return texture, width, height, GL_BGR

    @classmethod
    def get_tex_id(cls, occupation: str) -> int:
        return cls._occupated_textures[occupation]

    @classmethod
    def current_atlas(cls, width: int, height: int) -> Sequence[Atlas | Rec]:
        for atlas in cls._atlas_array:
            rect = atlas.insert(width, height)
            if not rect == None:
                return atlas, rect

        cls.new_atlas()
        atlas = cls._atlas_array[-1]
        rect = atlas.insert(width, height)

        return atlas, rect

    @classmethod
    def get_tex_id_atlas(cls, tex_id: int) -> Atlas:
        return cls._atlas_loc[tex_id]

    @classmethod
    def add_texture_atlas_list(cls, frames: Sequence[Draw], convert_type: ConvertType, location: list[UVLocation]) -> UVLocation:
        uv_list = []
        for i, frame in enumerate(frames):
            if len(location) == 0:
                loc = UVLocation("", None)
            else:
                loc = location[i]
                
            uv = cls.add_texture_atlas(frame, convert_type, loc)
            uv_list.append(uv)

        return uv_list

    @classmethod
    def remove_texture_atlas_list(cls, location: list[UVLocation]) -> None:
        for loc in location:
            cls.remove_texture_atlas(loc)

    @classmethod
    def add_texture_atlas(cls, texture: Draw, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, image_format = cls.byte_texture(texture, convert_type)

        if location.tex_id:
            key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)
            atlas = cls.get_tex_id_atlas(location.tex_id)

            if not atlas.used_rects.get(key) == None:
                if not width == location.uv.w or not height == location.uv.h:
                    raise ValueError("Tamanhos não batem")
                cls.replace_texture_atlas(texture, convert_type, location)
                return location

        current_atlas, rect = cls.current_atlas(width, height)

        glBindTexture(GL_TEXTURE_2D, current_atlas.tex_id)
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            rect.x, rect.y,
            rect.w, rect.h,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )
        return UVLocation(current_atlas.tex_id, rect)

    @classmethod
    def replace_texture_atlas(cls, texture: Draw, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, image_format = cls.byte_texture(texture, convert_type)
        glBindTexture(GL_TEXTURE_2D, location.tex_id)
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            location.uv.x, location.uv.y,
            location.uv.w, location.uv.h,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )

    @classmethod
    def remove_texture_atlas(cls, location: UVLocation) -> None:
        key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)

        atlas = cls.get_tex_id_atlas(location.tex_id)
        if not atlas.used_rects.get(key) == None:
            atlas.remove(location.uv)

            if len(atlas.used_rects) == 0 and len(cls._atlas_array) >= 2:
                ShaderHandler.remove_texture(atlas.occupation)
                del cls._atlas_loc[atlas.tex_id]
                cls._atlas_array.remove(atlas)

    @classmethod
    def add_texture(cls, texture: Draw, convert_type: ConvertType, occupation: str=None) -> tuple:
        if occupation == None:
            occupation = uuid.uuid4().hex
            
        if not cls._occupated_textures.get(occupation) == None:
            tex_id = cls._occupated_textures[occupation]
            width, height = cls.replace_texture(tex_id, texture, convert_type)

            return UVLocation(tex_id, Rec(x=0, y=0, w=width, h=height))
            
        image, width, height, image_format = cls.byte_texture(texture, convert_type)
        tex_id = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            image_format,
            GL_UNSIGNED_BYTE,
            image)

        cls._occupated_textures[occupation] = tex_id
        return UVLocation(tex_id, uv=Rec(x=0, y=0, w=width, h=height))
    
    @classmethod
    def replace_texture(cls, tex_id: int, texture: Draw, convert_type: ConvertType) -> int:
        glBindTexture(GL_TEXTURE_2D, tex_id)
        image, width, height, image_format = cls.byte_texture(texture, convert_type)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width, height,
            0,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )

        return width, height
    
    @classmethod
    def remove_texture(cls, occupation: str) -> None:
        glDeleteTextures([cls._occupated_textures[occupation]])
        cls._occupated_textures.pop(occupation)

    @staticmethod
    def ortho(left, right, bottom, top, near=-1, far=1) -> np.array:
        return np.array([
            [2/(right-left), 0, 0, -(right+left)/(right-left)],
            [0, 2/(top-bottom), 0, -(top+bottom)/(top-bottom)],
            [0, 0, -2/(far-near), -(far+near)/(far-near)],
            [0, 0, 0, 1]
        ], dtype=np.float32)
    
    @staticmethod
    def build_view(cam_pos, cam_angle, cam_scale, pivot) -> np.array:
        c = np.cos(radians(cam_angle))
        s = np.sin(radians(cam_angle))

        translation = np.array([
            [1, 0, 0, -cam_pos[0] - pivot[0]],
            [0, 1, 0, -cam_pos[1] - pivot[1]],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rotation = np.array([
            [ c, s, 0, pivot[0]],
            [-s, c, 0, pivot[1]],
            [ 0, 0, 1, 0],
            [ 0, 0, 0, 1]
        ], dtype=np.float32)

        scale = np.array([
            [1/cam_scale[0], 0, 0, 0],
            [0, 1/cam_scale[1], 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        return scale @ rotation @ translation

    @classmethod
    def render_add(cls, sprite) -> None:
        cls._render_list.append(sprite)

    @classmethod
    def render(cls, mvp: np.array, texture: Draw, data: np.array, unit=GL_TEXTURE0) -> None:
        glUniformMatrix4fv(cls.u_mvp_loc, 1, GL_TRUE, mvp)
        
        glBindBuffer(GL_ARRAY_BUFFER, cls.instance_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, data.nbytes, data)
        
        glActiveTexture(unit)
        glBindTexture(GL_TEXTURE_2D, texture)

        instance_count = len(data) // cls.stride_size

        glBindVertexArray(cls.vao)
        
        glDrawElementsInstanced(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None, instance_count)

    @classmethod
    def render_all(cls) -> None:
        mvp = cls.ortho(0, cls.screen_size[0], cls.screen_size[1], 0)
        cam = Camera.get_main_camera()
        cam_pos = cam.get_pos()
        cam_scale = cam.get_scale()
        cam_angle = cam.get_angle()
        view = cls.build_view(cam_pos, cam_angle, cam_scale, (cam_scale[0] * cls.screen_size[0] / 2, cam_scale[1] * cls.screen_size[1] / 2))
        
        batch = []
        last_id = float("-inf")
        last_unit = float("-inf")
        last_program = "def"

        for sprite in cls._render_list:
            same_program = True
            if not sprite.program == None and not sprite.program == last_program:
                same_program = False
                cls.set_shader(sprite.program)

            same_batch = sprite.tex_id == last_id and sprite.unit == last_unit and same_program
            if not same_batch and batch:
                    data = cls.build_instance_buffer(batch, view, cam_scale, cam_angle)
                    cls.render(mvp, last_id, data, last_unit)
                    batch = []

            batch.append(sprite)
            last_id = sprite.tex_id
            last_unit = sprite.unit
            if not sprite.program == None:
                last_program = sprite.program

        if batch:
            data = cls.build_instance_buffer(batch, view, cam_scale, cam_angle)
            cls.render(mvp, last_id, data, last_unit)

        cls._render_list = []

    @classmethod
    def build_instance_buffer(cls, sprites, view_matrix, cam_scale, cam_angle) -> np.array:
        data = []

        for s in sprites:
            x, y = s.pos
            w, h = s.scale
            rotation = s.rotation

            if not s.static:
                pos = np.array([x, y, 0.0, 1.0], dtype=np.float32)
                transformed = view_matrix @ pos
                x, y = transformed[0], transformed[1]

                w /= cam_scale[0]
                h /= cam_scale[1]
                rotation -= cam_angle

            cos_r = cos(radians(rotation))
            sin_r = sin(radians(rotation))

            u0 = s.uv.x / cls._atlas_size
            v0 = s.uv.y / cls._atlas_size
            us = s.uv.w / cls._atlas_size
            vs = s.uv.h / cls._atlas_size

            data.extend([
                x, y,
                w, h,
                cos_r, sin_r,
                u0, v0,
                us, vs,
            ])
            data.extend(s.overhead)

        return np.array(data, dtype=np.float32)