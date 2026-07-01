from sweet.graphics.texture import Imaging # type: ignore
from sweet.vector import Vec2, Vec3 # type: ignore
from pathlib import Path
import moderngl

from . import (
    camera, # type: ignore
    common, # type: ignore
    entity, # type: ignore
    graphics, # type: ignore
    inputting, # type: ignore
    linalg, # type: ignore
    looping, # type: ignore
    network, # type: ignore
    path_solver, # type: ignore
)

def init():
    looping.GameLoop.init()

def run():
    looping.GameLoop.start()

# class Scene:
#     @staticmethod
#     def add_entity(obj: type[object], *context: Any):
#         entity.EntityManager.agend_entity()

class Entity(entity.Entity):
    def __init__(
                self,
                pos: tuple[int, int] | tuple[int, int, int] = (0, 0),
                scale: tuple[int, int] | tuple[int, int, int] = (1, 1),
                angle: float | tuple[float, float, float] = 0,
                pre_tick: bool = False,
                tick: bool = False,
                pos_tick: bool = False
            ):
        super().__init__(
                pos,
                scale,
                angle,
                pre_tick,
                tick,
                pos_tick
        )

class Resources:
    @staticmethod
    def load_assets(path: str | Path):
        graphics.texture.Texture.load_json_textures(path)
        graphics.model.Model.load_json_models(path)
    
    @staticmethod
    def texture(name: str):
        return graphics.texture.Texture.get_texture(name)
    
    @staticmethod
    def model(name: str):
        return graphics.model.Model.get_model(name)

class Shader:
    @staticmethod
    def use(name: str):
        entity.Draw.set_state_shader(name)

    @staticmethod
    def add(path_vertex: str | Path, path_fragment: str | Path, name: str | None=None):
        if name is None:
            # Extracts the file name of the vertex shaders without the extension
            path_str = str(path_vertex)
            name = path_str.split("/")[-1].split(".")[0]
            
        return graphics.shaders.ShaderManager.add_shader(name, path_vertex, path_fragment)

    @staticmethod
    def new_fbo(size: tuple[int, int]) -> moderngl.Framebuffer:
        return graphics.shaders.ShaderTexture.create_fbo(size)
    
    @staticmethod
    def use_frame(fbo: moderngl.Framebuffer | None, depth_test: bool=True, clear_color: tuple[float, float, float, float]=(0, 0, 0, 1)):
        graphics.shaders.ShaderRender.set_frame_buffer(fbo, depth_test, clear_color)

    @staticmethod
    def force_draw():
        graphics.shaders.ShaderRender.render()

    @staticmethod
    def ubo(binding: int, name: str, type: str, *values: int | float):
        graphics.shaders.ShaderRender.add_ubo_data(binding, name, type, *values)

    @staticmethod
    def ssbo(binding: int, name: str, type: str, *values: int | float):
        graphics.shaders.ShaderRender.add_ssbo_data(binding, name, type, *values)

class Display:
    screen_size = (looping.GameLoop.view_width, looping.GameLoop.view_height)

    @staticmethod
    def size(size: tuple[int, int]) -> None:
        looping.GameLoop.set_screen_size(size)
        
    @staticmethod
    def resizable(value: bool) -> None:
        looping.GameLoop.set_resizable(value)
        
    @staticmethod
    def background(color: tuple[int, int, int, int]) -> None:
        looping.GameLoop.set_background_color(color)
        
    @staticmethod
    def maximizable(value: bool) -> None:
        looping.GameLoop.set_can_fullscreen(value)
    
    @staticmethod
    def is_maximized() -> bool:
        return looping.GameLoop.get_fullscreen()
    
    @staticmethod
    def title(text: str) -> None:
        looping.GameLoop.set_title(text)
    
__all__ = ["Resources", "Display"]