import moderngl
import moderngl_window as mglw
import glfw # type: ignore
from typing import Optional
from abc import ABC, abstractmethod
from sweet.core.system import state

class Renderer(ABC):
    @abstractmethod
    def use_context(cls) -> None:
        pass

class GLContext:
    _ctx: Optional[moderngl.Context] = None
    _has_context: bool = False

    @classmethod
    def use_context(cls, require: int = 330) -> moderngl.Context:
        if cls._has_context and cls._ctx is not None:
            return cls._ctx

        cls._ctx = moderngl.create_context(standalone=True, require=require)
        mglw.activate_context(ctx=cls._ctx)
        cls._has_context = True
        return cls._ctx

    @classmethod
    def has_context(cls) -> bool:
        return cls._has_context

    @classmethod
    def get_context(cls) -> moderngl.Context:
        if cls._ctx is None:
            raise RuntimeError("GLContext ainda não foi inicializado. Chame 'use_context()' primeiro.")
        return cls._ctx

    @classmethod
    def render_scene_to_target(cls, framebuffer: moderngl.Framebuffer):
        ctx = cls.get_context()
        framebuffer.use()
        ctx.clear(0.1, 0.2, 0.3)
        ...

    @classmethod
    def shutdown(cls):
        if not cls._has_context or cls._ctx is None:
            return

        cls._ctx.release()
        
        mglw.activate_context(ctx=None) # type: ignore
        
        cls._ctx = None
        cls._has_context = False

if state.engine.render == "GLCONTEXT":
    GLContext.use_context()