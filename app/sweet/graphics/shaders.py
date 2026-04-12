from ..common import FileType, Draw
import pygame as pg
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
from pathlib import Path
from math import sin, cos
from sweet.camera import Camera
from typing import Callable
import uuid

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

    _CWD = Path.cwd()
    _SHADERS = _CWD / "app" / "shaders"

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
        files: dict[str, str] = cls.get_shader_files()
        for key in files:
            vertex: str
            fragment: str
            vertex, fragment = files[key]["vertex"], files[key]["fragment"]
            cls._shader_files[key]["program"] = cls.create_shader_program(vertex, fragment)

    @classmethod
    def get_shader_files(cls) -> dict[str, str]:
        return cls._shader_files

    @classmethod
    def get_shader_program(cls, name: str) -> Callable:
        return cls._shader_files[name]["program"]

    @classmethod
    def set_default_file_path(cls, path: str) -> None:
        cls._SHADERS = path

    @classmethod
    def add_shader_file(cls, name: str) -> None:
        with open(cls._SHADERS / (name + ".vsh"), "r") as file:
            VERTEX_SHADER = file.read()
        with open(cls._SHADERS / (name + ".fsh"), "r") as file:
            FRAGMENT_SHADER = file.read()
        cls._shader_files[name] = {"vertex": VERTEX_SHADER, "fragment": FRAGMENT_SHADER}

    @staticmethod
    def create_shader_program(vertex: str, fragment: str) -> Callable:
        shader = compileProgram(
            compileShader(vertex, GL_VERTEX_SHADER),
            compileShader(fragment, GL_FRAGMENT_SHADER)
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

    @classmethod
    def set_mvp(cls, mvp: np.array) -> None:
        cls.u_mvp_loc = mvp

    @classmethod
    def set_shader(cls, shader: str, custom_mvp: np.array=None) -> None:
        shader_program = cls.get_shader_program(shader)
        glUseProgram(shader_program)
        cls._current_program = shader_program
        if custom_mvp == None:
            mvp = glGetUniformLocation(shader_program, "u_mvp")
        cls.set_mvp(mvp)

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
    def remove_texture(cls, occupation: str) -> None:
        glDeleteTextures([cls._occupated_textures[occupation]])
        cls._occupated_textures.pop(occupation)

    @staticmethod
    def replace_texture(tex_id: int, texture: Draw, save_type: FileType=FileType.PGSURF) -> int:
        glBindTexture(GL_TEXTURE_2D, tex_id)

        if save_type == FileType.PGSURF:
            image = pg.image.tostring(texture, "RGBA", True)
            width, height = texture.get_size()
        elif save_type == FileType.PILIMAGE:
            image = texture.tobytes("raw", "RGBA", 0, -1)
            width, height = texture.size
        
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width, height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            image
        )

        return tex_id

    @classmethod
    def add_texture(cls, texture, save_type=FileType.PGSURF, occupation: str=None) -> tuple:
        if occupation == None:
            occupation = uuid.uuid4().hex
        if not cls._occupated_textures.get(occupation) == None:
            tex_value = cls._occupated_textures[occupation]
            tex_id = cls.replace_texture(tex_value, texture, save_type)
            cls._occupated_textures[occupation] = tex_id
            source_format = save_type
            value = (tex_id, FileType.SHADERATLAS, texture, source_format, occupation)
            return value
            
        source_format: FileType
        if save_type == FileType.PGSURF:
            image = pg.image.tostring(texture, "RGBA", True)
            width, height = texture.get_size()
            source_format = FileType.PGSURF
        elif save_type == FileType.PILIMAGE:
            image = texture.tobytes("raw", "RGBA", 0, -1)
            width, height = texture.size
            source_format = FileType.PILIMAGE

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                    GL_RGBA, GL_UNSIGNED_BYTE, image)

        cls._occupated_textures[occupation] = tex_id
        value = (tex_id, FileType.SHADERATLAS, texture, source_format, occupation)
        return value
    
    @staticmethod
    def setup_textured_quad() -> list[int, int]:
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

        return VAO, EBO
    
    @classmethod
    def render(cls, mvp: np.array, texture: Draw, unit=GL_TEXTURE0) -> None:
        glUniformMatrix4fv(cls.u_mvp_loc, 1, GL_FALSE, mvp)
        glActiveTexture(unit)
        glBindTexture(GL_TEXTURE_2D, texture.get_image())
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)