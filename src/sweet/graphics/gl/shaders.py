from pathlib import Path
import json
from ...core import system
from pathlib import Path
from .introspection import Introspect, Introspection
import moderngl

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

class ShaderManager:
    _ctx: moderngl.Context
    _current_program: Shader = Shader("", "", "")
    _shaders: dict[str, Shader] = {}

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx

    @classmethod
    def load_json_shaders(cls, json_path: str | Path) -> None:
        absolute_path = system.solve_path(json_path)
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
        absolute_vertex = system.solve_path(path_vertex)
        absolute_fragment = system.solve_path(path_fragment)
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
            
            introspection = Introspect.introspect_program(program.glo)
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