"""
OPTIMIZED ModernGL HAL backend.

This is a drop-in replacement for the original hal/manager.py ModernGL
backend. Public class names, method signatures and behavior are kept
identical so existing call sites do not need to change. Every change is
marked with an "# OPT:" comment explaining the bottleneck it removes.

Summary of changes vs. the original:

1. Stable `.uid` identity for render targets (ModernGLFramebufferTarget,
   ModernGLCubemapTarget, ModernGLArrayTarget, ModernGLWindowTarget),
   mirroring the fix already applied to ModernGLGPUBuffer. The pipeline's
   VAO cache used to key on `id(target)`; once a target object is garbage
   collected, CPython is free to reuse that same address for an unrelated
   object, which could silently return a VAO built for a completely
   different (or already-released) render target. `.uid` is a
   monotonically increasing integer that is never reused.

2. `ModernGLGraphicsDevice.blit_texture_to_target` no longer creates and
   destroys a pair of native FBOs on every single call. This function
   runs at least once per view per frame (the final redirect-to-backbuffer
   step), so the old code was doing native FBO create/destroy churn every
   frame for what is, in practice, a small and stable set of texture
   pairs. FBO wrappers are now cached in a `weakref.WeakKeyDictionary`
   keyed on the *Python texture object* (not its GL name/`.glo`, which can
   be reused after deletion) with a `weakref.finalize` callback that
   releases the native FBO when the texture wrapper is garbage collected.
   This is both faster and safer than caching by `.glo`.

Everything else is unchanged from the original.
"""

import moderngl
import glfw
from sweet.plataform.hal.manager import *
from typing import Any, Optional, Callable, cast, Union
from sweet.plataform.hal.manager import Cubemap, RenderTarget
from .introspection import Introspect, Introspection
from sweet.core import system
import itertools
import math
import traceback
import weakref
import ctypes  # type: ignore
import numpy as np
from PIL import Image
import OpenGL.GL as gl
from OpenGL.GL import (
    GL_TEXTURE_CUBE_MAP,  # type: ignore
    GL_TEXTURE_CUBE_MAP_POSITIVE_X, GL_TEXTURE_CUBE_MAP_POSITIVE_Y, GL_TEXTURE_CUBE_MAP_POSITIVE_Z,  # type: ignore
    GL_TEXTURE_CUBE_MAP_NEGATIVE_X, GL_TEXTURE_CUBE_MAP_NEGATIVE_Y, GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,  # type: ignore
    glGenFramebuffers, glBindFramebuffer, glDeleteFramebuffers, glBlitFramebuffer,  # type: ignore
    glFramebufferTexture, glFramebufferTexture2D, glDrawBuffers, GL_DEPTH_BUFFER_BIT,  # type: ignore
    GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,  # type: ignore
    GL_FRAMEBUFFER_COMPLETE, glCheckFramebufferStatus,  # type: ignore
    GL_COLOR_BUFFER_BIT, GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, GL_TEXTURE_BASE_LEVEL,  # type: ignore
    GL_READ_FRAMEBUFFER, GL_DRAW_FRAMEBUFFER, GL_NEAREST,  # type: ignore
    glGetError, GL_NO_ERROR, glViewport, glGenFramebuffers, glBindFramebuffer, glClearColor, glClearDepth, glClear,  # type: ignore
)

gfx_device: "ModernGLGraphicsDevice"

# Set to True while debugging to get full tracebacks printed for every
# failed command and a GL error check after framebuffer operations.
DEBUG_GL = False

# OPT: a single shared uid source for every render-target flavor below,
# so `.uid` values are comparable/never collide across target types when
# used as VAO-cache or FBO-cache keys.
_render_target_uid_counter = itertools.count()


def _check_gl_error(context: str) -> None:
    if not DEBUG_GL:
        return
    err = glGetError()
    if err != GL_NO_ERROR:  # type: ignore
        system.warn(f"[GL] error {hex(err)} after {context}")  # type: ignore


class ModernGLTextureArrayDepth:
    def __init__(self, width: int, height: int, layers: int, dtype: str = "f2"):
        if layers <= 0:
            raise ValueError("Cascade count must be greater than zero")

        self.width = width
        self.height = height
        self.layers = layers
        self.dtype = dtype

        internal_format = (  # type: ignore
            gl.GL_DEPTH_COMPONENT32F if dtype in ("f2", "f4") else gl.GL_DEPTH_COMPONENT24  # type: ignore
        )

        self.glo = int(gl.glGenTextures(1))
        gl.glBindTexture(gl.GL_TEXTURE_2D_ARRAY, self.glo)  # type: ignore
        gl.glTexImage3D(
            gl.GL_TEXTURE_2D_ARRAY, 0, internal_format,  # type: ignore
            width, height, layers, 0,
            gl.GL_DEPTH_COMPONENT, gl.GL_FLOAT, None,  # type: ignore
        )

        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)  # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)  # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)  # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)  # type: ignore

        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_COMPARE_MODE, gl.GL_COMPARE_REF_TO_TEXTURE)  # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D_ARRAY, gl.GL_TEXTURE_COMPARE_FUNC, gl.GL_LEQUAL)  # type: ignore

        gl.glBindTexture(gl.GL_TEXTURE_2D_ARRAY, 0)  # type: ignore
        _check_gl_error("csm depth array texture creation")

    def use(self, location: int = 0) -> None:
        gl.glActiveTexture(gl.GL_TEXTURE0 + location)  # type: ignore
        gl.glBindTexture(gl.GL_TEXTURE_2D_ARRAY, self.glo)  # type: ignore

    def release(self) -> None:
        if self.glo:
            gl.glDeleteTextures(1, [self.glo])
            self.glo = 0


class ModernGLArrayTarget(RenderTarget):

    def __init__(self, depth_array: ModernGLTextureArrayDepth, width: int, height: int):
        self.depth_array = depth_array
        self._size = (width, height)
        self.fbo_id: Optional[int] = None
        # OPT: stable identity for VAO/FBO caching (see module docstring).
        self.uid = next(_render_target_uid_counter)
        self._create_framebuffer()

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def is_layered(self) -> bool:
        return True

    def _create_framebuffer(self) -> None:
        fbo = gl.glGenFramebuffers(1)  # type: ignore
        if isinstance(fbo, (list, tuple, np.ndarray)):
            fbo = int(fbo[0])
        self.fbo_id = int(fbo)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo_id)  # type: ignore

        gl.glFramebufferTexture(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, self.depth_array.glo, 0)  # type: ignore

        gl.glDrawBuffer(gl.GL_NONE)  # type: ignore
        gl.glReadBuffer(gl.GL_NONE)  # type: ignore

        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)  # type: ignore
        _check_gl_error("csm layered framebuffer construction")
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)  # type: ignore

        if status != gl.GL_FRAMEBUFFER_COMPLETE:  # type: ignore
            self.release_resources()
            raise RuntimeError(f"Layered CSM framebuffer incomplete: {hex(status)}")  # type: ignore

    def use(self) -> None:
        if self.fbo_id is None:
            raise RuntimeError("CSM framebuffer has already been released")
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo_id)  # type: ignore
        gl.glViewport(0, 0, *self._size)  # type: ignore
        _check_gl_error("csm target bind")

    def clear(self, color: tuple[float, float, float] = (0.0, 0.0, 0.0), depth: float = 1.0) -> None:
        gl.glClearDepth(depth)  # type: ignore
        gl.glClear(gl.GL_DEPTH_BUFFER_BIT)  # type: ignore

    def unbind(self) -> None:
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)  # type: ignore

    def release(self) -> None:
        self.unbind()
        self.release_resources()

    def release_resources(self) -> None:
        if self.fbo_id is not None:
            gl.glDeleteFramebuffers(1, [self.fbo_id])
            self.fbo_id = None

    def native_handle(self) -> int:
        if self.fbo_id is None:
            raise RuntimeError("CSM framebuffer has been released")
        return self.fbo_id

    @property
    def color_attachments(self) -> list[Any]:
        return []

    @property
    def depth_attachment(self) -> ModernGLTextureArrayDepth:
        return self.depth_array


class ModernGLArrayFramebuffer(ArrayFramebuffer):
    def __init__(self, width: int, height: int, layers: int, dtype: str = "f2"):
        self.width = width
        self.height = height
        self.layers = layers
        self.depth_array = ModernGLTextureArrayDepth(width, height, layers, dtype)
        self._target = ModernGLArrayTarget(self.depth_array, width, height)

    def get_target(self) -> RenderTarget:
        return self._target

    def release(self) -> None:
        self._target.release()
        self.depth_array.release()


class ModernGLTexture2D(Texture2D):
    def __init__(self, width: int, height: int, components: int = 4, dtype: str = "f1"):
        self.ctx = gfx_device.ctx
        self.width = width
        self.height = height
        self.dtype = dtype
        self.texture: moderngl.Texture = self.ctx.texture((width, height), components, dtype=dtype)

    def upload_pixels(self, data: Any, x: int = 0, y: int = 0, width: Optional[int] = None, height: Optional[int] = None):
        w = width if width is not None else (self.width - x)
        h = height if height is not None else (self.height - y)

        viewport = (x, y, w, h)

        self.texture.write(data, viewport=viewport)

    def build_mipmaps(self, base: int = 0, max_level: int = 1000) -> None:
        self.texture.build_mipmaps(base=base, max_level=max_level)

    def set_filters(self, min_filter: Any, mag_filter: Any) -> None:
        self.texture.filter = (min_filter, mag_filter)

    @property
    def mip_levels(self) -> int:
        return int(math.floor(math.log2(max(self.width, self.height)))) + 1

    def release(self):
        if self.texture:
            self.texture.release()


class ModernGLCubemap(Cubemap):
    """OpenGL cubemap resource backed by a layered framebuffer.

    Rendering a cubemap is a SINGLE render operation. The framebuffer is
    layered (glFramebufferTexture), and the geometry shader is responsible
    for routing primitives to layers 0..5 through gl_Layer.
    """

    def __init__(
        self,
        size: int,
        color_formats: list[int],
        components: int,
        dtype: str = "f1",
    ):
        if size <= 0:
            raise ValueError("Cubemap size must be greater than zero")
        if components not in (1, 2, 3, 4):
            raise ValueError("Cubemap components must be 1, 2, 3, or 4")

        self.ctx = gfx_device.ctx
        self.size = int(size)
        self.color_formats = color_formats
        self.components = components
        self.dtype = dtype

        self._cubemap: moderngl.TextureCube = self.ctx.texture_cube(
            size=(self.size, self.size),
            components=components,
            dtype=dtype,
        )

        self._cubemap.repeat_x = False  # type: ignore
        self._cubemap.repeat_y = False  # type: ignore

        self._target = ModernGLCubemapTarget(
            self.ctx,
            self._cubemap,
            self.size,
        )

    @property
    def texture(self) -> moderngl.TextureCube:
        return self._cubemap

    def get_target(self) -> RenderTarget:
        return self._target

    def set_filters(self, *filters: Any):
        if len(filters) != 2:
            raise ValueError("set_filters expects (min_filter, mag_filter)")
        self._cubemap.filter = filters

    def build_mipmaps(self, base: int = 0, max_level: int = 1000) -> None:
        self._cubemap.build_mipmaps(base=base, max_level=max_level)

    def release(self):
        self._target.release()
        self._cubemap.release()


class ModernGLCubemapTarget(RenderTarget):
    """Layered render target for a cubemap.

    glFramebufferTexture attaches the complete cubemap as a layered
    framebuffer attachment. A geometry shader can then set gl_Layer to
    0..5 and emit the primitive into all six faces in one draw call.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        cubemap_texture: moderngl.TextureCube,
        size: int,
    ):
        self.ctx = ctx
        self._size = int(size)
        self.cubemap = cubemap_texture
        self.fbo_id: Optional[int] = None
        # OPT: stable identity for VAO/FBO caching (see module docstring).
        self.uid = next(_render_target_uid_counter)
        self._create_framebuffer()

    @property
    def size(self) -> tuple[int, int]:
        return (self._size, self._size)

    @property
    def is_layered(self) -> bool:
        return True

    def _create_framebuffer(self) -> None:
        fbo = glGenFramebuffers(1)  # type: ignore
        if isinstance(fbo, (list, tuple, np.ndarray)):
            fbo = int(fbo[0])
        self.fbo_id = int(fbo)

        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_id)

        glFramebufferTexture(
            GL_FRAMEBUFFER,
            GL_COLOR_ATTACHMENT0,
            self.cubemap.glo,
            0,
        )
        glDrawBuffers([GL_COLOR_ATTACHMENT0])

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        _check_gl_error("layered cubemap framebuffer construction")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        if status != GL_FRAMEBUFFER_COMPLETE:
            self.release_resources()
            raise RuntimeError(
                f"Layered cubemap framebuffer incomplete: {hex(status)}"  # type: ignore
            )

    def use(self, face_index: Optional[int] = None) -> None:
        if self.fbo_id is None:
            raise RuntimeError("Cubemap framebuffer has already been released")

        if face_index is not None and not 0 <= face_index < 6:
            raise ValueError(
                f"face_index must be in range [0, 5], got {face_index}"
            )

        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_id)
        glViewport(0, 0, self._size, self._size)
        _check_gl_error("layered cubemap target bind")

    def clear(
        self,
        color: tuple[float, float, float] = (0.0, 0.0, 0.0),
        depth: float = 1.0,
    ):
        glClearColor(color[0], color[1], color[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT)  # type: ignore

    def unbind(self) -> None:
        self.ctx.screen.use()

    def release(self):
        self.unbind()
        self.release_resources()

    def release_resources(self):
        if self.fbo_id is not None:
            glDeleteFramebuffers(1, [self.fbo_id])
            self.fbo_id = None

    def native_handle(self) -> int:
        if self.fbo_id is None:
            raise RuntimeError("Cubemap framebuffer has been released")
        return self.fbo_id

    @property
    def color_attachments(self) -> list[moderngl.TextureCube]:
        return [self.cubemap]

    @property
    def depth_attachment(self) -> None:
        return None

    @property
    def color_textures(self) -> list[moderngl.TextureCube]:
        return [self.cubemap]


class ModernGLFramebufferTarget(RenderTarget):
    def __init__(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        color_formats: list[Any] = [4],
        has_depth: bool = True,
        dtype: str = "f1",
        color_dtypes: Optional[list[Optional[str]]] = None,
    ):
        self.ctx = ctx
        self._size = (width, height)
        self._color_textures: list[Any] = []
        self._is_cubemap = False
        self._owns_color_textures: list[bool] = []
        # OPT: stable identity for VAO/FBO caching (see module docstring).
        self.uid = next(_render_target_uid_counter)

        mgl_color_attachments: list[Any] = []

        for i, fmt in enumerate(color_formats):
            if isinstance(fmt, int):
                attachment_dtype = dtype
                if color_dtypes is not None and i < len(color_dtypes) and color_dtypes[i] is not None:
                    attachment_dtype = color_dtypes[i]  # type: ignore
                tex = ModernGLTexture2D(width, height, components=fmt, dtype=attachment_dtype)  # type: ignore
                owns = True
            else:
                tex = cast(ModernGLTexture2D, fmt)
                owns = False
            self._color_textures.append(tex)
            self._owns_color_textures.append(owns)
            mgl_color_attachments.append(tex.texture)

        self._depth_texture: Optional[ModernGLTexture2D] = None
        mgl_depth_attachment: Optional[moderngl.Texture] = None

        if has_depth:
            depth_mgl_tex = ctx.depth_texture((width, height))

            self._depth_texture = ModernGLTexture2D.__new__(ModernGLTexture2D)
            self._depth_texture.ctx = ctx
            self._depth_texture.width = width
            self._depth_texture.height = height
            self._depth_texture.dtype = dtype
            self._depth_texture.texture = depth_mgl_tex
            mgl_depth_attachment = depth_mgl_tex

        self._native_handle = ctx.framebuffer(
            color_attachments=mgl_color_attachments,
            depth_attachment=mgl_depth_attachment,
        )

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def color_attachments(self) -> list[Texture2D]:
        return self._native_handle.color_attachments  # type: ignore

    def get_color_texture(self, index: int = 0) -> Texture2D:
        if not self._color_textures:
            raise IndexError("This RenderTarget has no color attachments")
        return self._color_textures[index]

    @property
    def depth_attachment(self) -> Optional[ModernGLTexture2D]:
        return self._native_handle.depth_attachment  # type: ignore

    def native_handle(self) -> Any:
        return self._native_handle

    def use(self):
        self._native_handle.use()

    def clear(self, color: tuple[float, float, float] = (0.0, 0.0, 0.0), depth: float = 1.0):
        self._native_handle.clear(color=(*color, 1.0), depth=depth)

    def release(self) -> None:
        for tex, owns in zip(self._color_textures, self._owns_color_textures):
            if owns:
                tex.release()
        if self._depth_texture is not None:
            self._depth_texture.release()
        self._native_handle.release()


class ModernGLVertexLayout(VertexLayout):
    def __init__(self, layout_format: Optional[str], attributes: Optional[list[str]]):
        self.format_str = layout_format
        self.attributes = attributes

    def bind(self) -> None:
        pass

    def release(self) -> None:
        pass


class ModernGLGPUBuffer(GPUBuffer):
    # Monotonically increasing counter gives every buffer a stable
    # identity for the pipeline's VAO cache; `id(obj)` is not safe here
    # because a freed buffer's address can be reused by an unrelated
    # object, which would let a stale VAO cache entry silently point at
    # the wrong (or freed) GPU buffer.
    _uid_counter = itertools.count()

    def __init__(self, size: int, dynamic: bool = False) -> None:
        self.ctx = gfx_device.ctx
        self._size = size
        self.buffer: moderngl.Buffer = self.ctx.buffer(reserve=size, dynamic=dynamic)
        self.uid = next(ModernGLGPUBuffer._uid_counter)

    @property
    def size(self) -> int:
        return self._size

    def upload_data(self, data: Any, offset: int = 0):
        self.buffer.write(data, offset=offset)

    def read_data(self, size: int = -1, offset: int = 0) -> bytes:
        return self.buffer.read(size=size, offset=offset)

    def release(self):
        if self.buffer:
            self.buffer.release()


class ModernGLResourceLayout(ResourceLayout):
    def __init__(self, bindings: list[tuple[int, ResourceType]]):
        super().__init__(bindings)


class ModernGLGPUShader(GPUShader):
    def __init__(self, source: Any):
        self.program: moderngl.Program = gfx_device.ctx.program(
            vertex_shader=source.vertex, fragment_shader=source.fragment, geometry_shader=source.geometry
        )
        self._introspection = Introspect.introspect_program(self.program.glo)

    def set_program_location(self, name: str, value: int) -> None:
        self.program[name].value = value  # type: ignore

    def get_introspection(self) -> Introspection:
        return self._introspection

    def bind(self):
        pass

    def release(self):
        if self.program:
            self.program.release()


class ModernGLResourceSet(ResourceSet):
    def __init__(self, layout: ModernGLResourceLayout):
        self.layout = layout
        self.bound_resources: dict[int, ResourceBinding] = {}

    def _slot_declared(self, slot: int) -> bool:
        bindings = self.layout.bindings
        if isinstance(bindings, dict):  # type: ignore
            return slot in bindings
        try:
            return any(entry[0] == slot for entry in bindings)  # type: ignore
        except (TypeError, IndexError):
            return True

    def update(self, bindings: list[ResourceBinding]) -> None:
        for b in bindings:
            if not self._slot_declared(b.binding_slot):
                raise ValueError(
                    f"Binding {b.binding_slot} não possui um slot declarado em layout"
                )
            self.bound_resources[b.binding_slot] = b

    def apply(self, set_index_offset: int = 0):
        for slot, binding in self.bound_resources.items():
            actual_slot = slot + set_index_offset

            if binding.resource_type == ResourceType.UNIFORM_BUFFER:
                res = binding.resource
                if isinstance(res, BufferBinding):
                    res.buffer.buffer.bind_to_uniform_block(actual_slot, offset=res.offset, size=res.size)  # type: ignore
                else:
                    res.buffer.bind_to_uniform_block(actual_slot)  # type: ignore

            elif binding.resource_type == ResourceType.STORAGE_BUFFER:
                res = binding.resource
                if isinstance(res, BufferBinding):
                    res.buffer.buffer.bind_to_storage_buffer(actual_slot, offset=res.offset, size=res.size)  # type: ignore
                else:
                    res.buffer.bind_to_storage_buffer(actual_slot)  # type: ignore

            elif binding.resource_type == ResourceType.TEXTURE_2D:
                tex: ModernGLTexture2D = binding.resource  # type: ignore
                tex.texture.use(location=actual_slot)


class ModernGLWindowTarget(RenderTarget):
    def __init__(self, window: Any = None):
        self.ctx = gfx_device.ctx
        self.window = window
        # OPT: stable identity for VAO/FBO caching (see module docstring).
        self.uid = next(_render_target_uid_counter)

    def make_current(self):
        if self.window and hasattr(self.window, "make_current"):
            self.window.make_current()
            gl.glEnable(gl.GL_TEXTURE_CUBE_MAP_SEAMLESS)  # type: ignore

            if hasattr(self.window, "size"):
                w, h = self.window.size
                self.ctx.viewport = (0, 0, w, h)

            self.ctx.screen.use()

    @property
    def size(self) -> tuple[int, int]:
        return self.window._size

    @property
    def color_attachments(self) -> list[Texture2D]:
        return []  # type: ignore

    @property
    def depth_attachment(self) -> Optional[Texture2D]:
        return None

    def use(self):
        self.ctx.screen.use()

    def clear(self, color: tuple[float, float, float] = (0.0, 0.0, 0.0), depth: float = 1.0):
        self.ctx.clear(*color, depth=depth)

    def native_handle(self) -> moderngl.Framebuffer:
        return self.ctx.screen

    def release(self) -> None:
        pass


class ModernGLRenderPipeline(RenderPipeline):
    def __init__(self, descriptor: RenderPipelineDescriptor):
        self.ctx = gfx_device.ctx
        self.descriptor = descriptor
        if not isinstance(descriptor.shader, ModernGLGPUShader):
            raise TypeError(
                "Implementação precisa ser compatível com ModernGLGPUShader"
            )
        self.program: moderngl.Program = descriptor.shader.program

        topologies = {
            "triangles": moderngl.TRIANGLES,
            "lines": moderngl.LINES,
            "points": moderngl.POINTS,
            "triangle_strip": moderngl.TRIANGLE_STRIP,
        }
        self.mode = topologies.get(descriptor.primitive_topology, moderngl.TRIANGLES)

        # Cache key uses stable buffer.uid / target.uid instead of id(vbo)/id(ibo)/id(target).
        self._vao_cache: dict[
            tuple[int, int, Optional[int], int], moderngl.VertexArray
        ] = {}
        # A single cached attributeless VAO, reused across every
        # bindless/attributeless draw call instead of allocating a new one
        # per draw.
        self._empty_vao: Optional[moderngl.VertexArray] = None

    def get_or_create_vao(
        self,
        target_id: int,
        vbo: ModernGLGPUBuffer,
        ibo: Optional[ModernGLGPUBuffer] = None,
        base_vertex: int = 0,
    ) -> moderngl.VertexArray:
        vbo_key = vbo.uid
        ibo_key = ibo.uid if ibo is not None else None
        cache_key = (target_id, vbo_key, ibo_key, base_vertex)

        if cache_key not in self._vao_cache:
            layout = cast(ModernGLVertexLayout, self.descriptor.vertex_layout)
            index_buffer = ibo.buffer if ibo else None
            if layout.attributes is None or layout.format_str is None:
                self._vao_cache[cache_key] = self.ctx.vertex_array(  # type: ignore
                    self.program, []
                )
                return self._vao_cache[cache_key]

            buffer_spec = (vbo.buffer, layout.format_str, *layout.attributes)

            if base_vertex > 0:
                buffer_spec = (
                    vbo.buffer,
                    layout.format_str,
                    *layout.attributes,
                    base_vertex,
                )

            self._vao_cache[cache_key] = self.ctx.vertex_array(  # type: ignore
                self.program, [buffer_spec], index_buffer=index_buffer
            )

        return self._vao_cache[cache_key]

    def get_or_create_empty_vao(self) -> moderngl.VertexArray:
        if self._empty_vao is None:
            self._empty_vao = self.ctx.vertex_array(self.program, [])  # type: ignore
        return self._empty_vao

    def apply_state(self):
        if self.descriptor.depth_test_enable:
            self.ctx.enable(moderngl.DEPTH_TEST)

            depth_ops = {
                "never": "0",
                "less": "<",
                "equal": "==",
                "less_equal": "<=",
                "greater": ">",
                "not_equal": "!=",
                "greater_equal": ">=",
                "always": "1"
            }

            op = self.descriptor.depth_compare_op.lower()
            self.ctx.depth_func = depth_ops.get(op, "<")
        else:
            self.ctx.disable(moderngl.DEPTH_TEST)

        front_face = getattr(self.descriptor, "front_face", "ccw")
        self.ctx.front_face = front_face

        cull_mode = self.descriptor.cull_mode.lower()
        if cull_mode != "none":
            self.ctx.enable(moderngl.CULL_FACE)

            if cull_mode in ["front", "back", "front_and_back"]:
                self.ctx.cull_face = cull_mode
            else:
                if "back" in cull_mode:
                    self.ctx.cull_face = "back"
                elif "front" in cull_mode:
                    self.ctx.cull_face = "front"
        else:
            self.ctx.disable(moderngl.CULL_FACE)

        if self.descriptor.blend_enabled:
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.ONE, moderngl.ONE
            self.ctx.blend_equation = moderngl.FUNC_ADD
        else:
            self.ctx.disable(moderngl.BLEND)

    def release(self):
        for vao in self._vao_cache.values():
            vao.release()
        self._vao_cache.clear()
        if self._empty_vao is not None:
            self._empty_vao.release()
            self._empty_vao = None


class ModernGLCommandBuffer(CommandBuffer):
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._commands: list[Callable[..., Any]] = []

        self._current_pipeline: Optional[ModernGLRenderPipeline] = None
        self._current_target: Optional[RenderTarget] = None
        self._current_resource_sets: dict[int, ModernGLResourceSet] = {}
        self._current_vbo: Optional[ModernGLGPUBuffer] = None
        self._current_ibo: Optional[ModernGLGPUBuffer] = None

    def begin(self) -> None:
        self._commands.clear()
        self._current_pipeline = None
        self._current_target = None
        self._current_resource_sets.clear()
        self._current_vbo = None
        self._current_ibo = None

    def begin_render_pass(
        self,
        target: RenderTarget,
        viewport: Optional[tuple[int, int, int, int]] = None,
        clear_color: tuple[float, float, float] = (0.1, 0.2, 0.3),
        face_index: Optional[int] = None,
        target_mip: Optional[int] = None,
    ) -> None:
        self._current_target = target

        def cmd_begin_pass(
            t: RenderTarget = target,
            vp: Optional[tuple[int, int, int, int]] = viewport,
            cc: tuple[float, float, float] = clear_color,
            face: Optional[int] = face_index,
            mip: Optional[int] = target_mip,
        ):
            if hasattr(t, "make_current"):
                t.make_current()  # type: ignore

            if isinstance(t, ModernGLCubemapTarget):
                t.use(face)

                w, h = t.size
                if mip is not None and mip > 0:
                    w, h = max(1, w >> mip), max(1, h >> mip)

                effective_vp = vp if vp is not None else (0, 0, w, h)
                glViewport(*effective_vp)
                t.clear(color=cc)
                return

            if isinstance(t, ModernGLArrayTarget):
                t.use()
                w, h = t.size
                if mip is not None and mip > 0:
                    w, h = max(1, w >> mip), max(1, h >> mip)

                effective_vp = vp if vp is not None else (0, 0, w, h)
                glViewport(*effective_vp)
                t.clear(color=cc)
                return

            w, h = t.size
            if mip is not None and mip > 0:
                w, h = max(1, w >> mip), max(1, h >> mip)

            if hasattr(t, "use_mip") and mip is not None:
                fb = t.use_mip(mip)
            else:
                fb = t.native_handle()
                if hasattr(fb, "use"):
                    if mip is not None and hasattr(fb, "use_mip"):
                        fb.use_mip(mip)
                    else:
                        fb.use()

            effective_vp = vp if vp is not None else (0, 0, w, h)

            if w > 0 and h > 0:
                self.ctx.viewport = effective_vp

            fb.clear(color=cc)

        self._commands.append(cmd_begin_pass)

    def set_pipeline(self, pipeline: RenderPipeline) -> None:
        if not isinstance(pipeline, ModernGLRenderPipeline):
            raise TypeError("Pipeline deve ser compatível com a implementação HAL")
        self._current_pipeline = pipeline

        def cmd_set_pipeline(
            p: ModernGLRenderPipeline = pipeline,
            target: Optional[RenderTarget] = self._current_target,
        ):
            if isinstance(target, ModernGLCubemapTarget):
                p.apply_state()
                self.ctx.disable(moderngl.CULL_FACE)
                self.ctx.disable(moderngl.DEPTH_TEST)
            else:
                p.apply_state()

        self._commands.append(cmd_set_pipeline)

    def set_resource_set(self, set_index: int, resource_set: ResourceSet) -> None:
        if not isinstance(resource_set, ModernGLResourceSet):
            raise TypeError("ResourceSet deve ser compatível com a implementação HAL")
        self._current_resource_sets[set_index] = resource_set
        offset = set_index * 8

        def cmd_set_resources():
            resource_set.apply(set_index_offset=offset)

        self._commands.append(cmd_set_resources)

    def set_vertex_buffer(self, slot: int, buffer: GPUBuffer, offset: int = 0) -> None:
        if not isinstance(buffer, ModernGLGPUBuffer):
            raise TypeError("Buffer deve ser compatível com a implementação HAL")
        self._current_vbo = buffer

    def set_index_buffer(
        self, buffer: GPUBuffer, index_type: str = "uint32", offset: int = 0
    ) -> None:
        if not isinstance(buffer, ModernGLGPUBuffer):
            raise TypeError("Buffer deve ser compatível com a implementação HAL")
        self._current_ibo = buffer

    def use_texture(
        self, src_texture: Any, location: int
    ) -> None:
        def use():
            if src_texture is None:
                system.warn(f"Tentativa de usar textura nula em location: {location}")
                return
            if isinstance(src_texture, ModernGLTexture2D):
                src_texture.texture.use(location=location)  # type: ignore
            elif isinstance(src_texture, ModernGLCubemap):
                src_texture._cubemap.use(location=location)  # type: ignore
            else:
                src_texture.use(location=location)  # type: ignore

        self._commands.append(use)

    def set_blend_state(
        self,
        enabled: bool = True,
        src_factor: str = "ONE",
        dst_factor: str = "ZERO",
        blend_op: str = "ADD",
        src_alpha_factor: Optional[str] = None,
        dst_alpha_factor: Optional[str] = None,
    ) -> None:
        BLEND_FACTORS = {
            "ZERO": moderngl.ZERO,
            "ONE": moderngl.ONE,
            "SRC_COLOR": moderngl.SRC_COLOR,
            "ONE_MINUS_SRC_COLOR": moderngl.ONE_MINUS_SRC_COLOR,
            "SRC_ALPHA": moderngl.SRC_ALPHA,
            "ONE_MINUS_SRC_ALPHA": moderngl.ONE_MINUS_SRC_ALPHA,
            "DST_ALPHA": moderngl.DST_ALPHA,
            "ONE_MINUS_DST_ALPHA": moderngl.ONE_MINUS_DST_ALPHA,
            "DST_COLOR": moderngl.DST_COLOR,
            "ONE_MINUS_DST_COLOR": moderngl.ONE_MINUS_DST_COLOR,
            "SRC_ALPHA_SATURATE": getattr(moderngl, "SRC_ALPHA_SATURATED", 0x0308),
            "SRC_ALPHA_SATURATED": getattr(moderngl, "SRC_ALPHA_SATURATED", 0x0308),
        }

        BLEND_OPS = {
            "ADD": getattr(moderngl, "FUNC_ADD", 0x8006),
            "SUBTRACT": getattr(moderngl, "FUNC_SUBTRACT", 0x800A),
            "REVERSE_SUBTRACT": getattr(moderngl, "FUNC_REVERSE_SUBTRACT", 0x800B),
            "MIN": getattr(moderngl, "MIN", 0x8007),
            "MAX": getattr(moderngl, "MAX", 0x8008),
        }

        s_rgb = BLEND_FACTORS.get(src_factor.upper(), moderngl.ONE)
        d_rgb = BLEND_FACTORS.get(dst_factor.upper(), moderngl.ZERO)
        s_a = BLEND_FACTORS.get((src_alpha_factor or src_factor).upper(), s_rgb)
        d_a = BLEND_FACTORS.get((dst_alpha_factor or dst_factor).upper(), d_rgb)
        op = BLEND_OPS.get(blend_op.upper(), getattr(moderngl, "FUNC_ADD", 0x8006))

        def apply_blend():
            ctx = self.ctx

            if not enabled:
                ctx.disable(moderngl.BLEND)
                return

            ctx.enable(moderngl.BLEND)
            ctx.blend_equation = op
            ctx.blend_func = (s_rgb, d_rgb, s_a, d_a)

        self._commands.append(apply_blend)

    def use_target_texture(
        self,
        src_render_target: RenderTarget,
        src_attachment: int,
        location: int,
        src_mip: int = 0,
    ) -> None:
        def use():
            if isinstance(src_render_target, ModernGLCubemapTarget):
                if src_attachment != 0:
                    raise ValueError("Cubemap targets currently expose one color attachment at index 0")
                src_render_target.cubemap.use(location=location)
                return

            if isinstance(src_render_target, ModernGLArrayTarget):
                src_render_target.depth_array.use(location=location)
                return

            native = src_render_target.native_handle()

            if src_attachment == -1:
                texture = native.depth_attachment
                if texture is None:
                    raise ValueError("RenderTarget has no depth attachment")
            else:
                colors = native.color_attachments
                if src_attachment < 0 or src_attachment >= len(colors):
                    raise IndexError(f"Color attachment {src_attachment} out of bounds")
                texture = colors[src_attachment]

            raw_tex = texture.texture if hasattr(texture, "texture") else texture

            if hasattr(raw_tex, "base_level"):
                raw_tex.base_level = src_mip
                raw_tex.max_level = src_mip

            raw_tex.use(location=location)

        self._commands.append(use)

    def set_uniform_value(self, uniform: str, value: bytes):
        pipeline = self._current_pipeline
        uniform = uniform[:-3] if uniform.endswith("[0]") else uniform

        def set_uniform():
            if pipeline and uniform in pipeline.program:
                pipeline.program[uniform].write(value)  # type: ignore

        self._commands.append(set_uniform)

    def draw(
        self,
        domain: str,
        vertex_count: int,
        instance_count: int = 1,
        first_vertex: int = 0,
        first_instance: int = 0,
    ) -> None:
        pipeline = self._current_pipeline
        vbo = self._current_vbo
        target = self._current_target

        if pipeline is None:
            raise RuntimeError("draw() chamado sem um pipeline vinculado")

        if vbo is None:
            def empty_cmd(p: ModernGLRenderPipeline = pipeline, vc: int = vertex_count,
                          ic: int = instance_count, fv: int = first_vertex):
                vao = p.get_or_create_empty_vao()
                vao.render(mode=p.mode, vertices=vc, instances=ic, first=fv)

            self._commands.append(empty_cmd)
            return

        # OPT: was `id(t)` -- a freed target's address can be reused,
        # which used to risk silently reusing a VAO built for a different
        # render target. `.uid` is stable and never reused.
        def cmd_draw(
            p: ModernGLRenderPipeline = pipeline,
            v: ModernGLGPUBuffer = vbo,
            t: Optional[RenderTarget] = target,
            vc: int = vertex_count,
            ic: int = instance_count,
            fv: int = first_vertex,
        ):
            target_key = getattr(t, "uid", 0) if t is not None else 0
            vao = p.get_or_create_vao(target_key, v, None, base_vertex=0)
            vao.render(mode=p.mode, vertices=vc, instances=ic, first=fv)

        self._commands.append(cmd_draw)

    def draw_indexed(
        self,
        index_count: int,
        instance_count: int = 1,
        first_index: int = 0,
        base_vertex: int = 0,
        first_instance: int = 0,
    ) -> None:
        p, v, i, t = (
            self._current_pipeline,
            self._current_vbo,
            self._current_ibo,
            self._current_target,
        )

        if p is None or v is None or i is None or t is None:
            raise RuntimeError(
                "Pipeline, VBO, IBO e Target precisam estar configurados antes do draw_indexed call"
            )

        # OPT: was `id(t)` -- see cmd_draw above for why `.uid` is required
        # for correctness, not just style.
        def cmd_draw_indexed(
            p: ModernGLRenderPipeline = p,
            v: ModernGLGPUBuffer = v,
            i: Optional[ModernGLGPUBuffer] = i,
            t: RenderTarget = t,
            ic: int = index_count,
            fi: int = first_index,
            bv: int = base_vertex,
            inst: int = instance_count,
            first_inst: int = first_instance,
        ):
            vao = p.get_or_create_vao(getattr(t, "uid", 0), v, i, base_vertex=bv)
            vao.render(mode=p.mode, vertices=ic, instances=inst, first=fi)

        self._commands.append(cmd_draw_indexed)

    def _save_attachment_image(
        self,
        fbo: Any,
        attachment_index: Union[int, str],
        filename: str,
        near: float = 0.1,
        far: float = 100.0,
    ):
        width, height = fbo.size
        is_depth = attachment_index in (-1, "depth")

        if is_depth:
            raw_bytes = fbo.read(
                viewport=(0, 0, width, height),
                components=1,
                attachment=-1,
                dtype="f4",
            )

            depth_data = np.frombuffer(raw_bytes, dtype=np.float32).reshape(
                (height, width)
            )

            depth_data = (2.0 * near * far) / (
                far + near - (2.0 * depth_data - 1.0) * (far - near)
            )
            depth_data = (depth_data - near) / (far - near)

            depth_grayscale = (np.clip(depth_data, 0.0, 1.0) * 255.0).astype(
                np.uint8
            )

            img = Image.fromarray(depth_grayscale, mode="L")

        else:
            idx = int(attachment_index)
            if len(fbo.color_attachments) <= idx:
                return

            attachment_texture = fbo.color_attachments[idx]

            channels = attachment_texture.components
            texture_dtype = attachment_texture.dtype

            raw_bytes = fbo.read(
                viewport=(0, 0, width, height),
                components=channels,
                attachment=idx,
                dtype=texture_dtype,
            )

            np_dtype = self._MGL_DTYPE_TO_NUMPY.get(texture_dtype, np.uint8)
            np_data = np.frombuffer(raw_bytes, dtype=np_dtype)

            if np_dtype in (np.float16, np.float32):
                np_data = (np.clip(np_data.astype(np.float32), 0.0, 1.0) * 255.0).astype(np.uint8)
            elif np_dtype != np.uint8:
                info = np.iinfo(np_dtype)
                np_data = (
                    (np_data.astype(np.float32) - info.min) / (info.max - info.min) * 255.0
                ).astype(np.uint8)

            if channels == 1:
                parsed = np_data.reshape((height, width))
            else:
                parsed = np_data.reshape((height, width, channels))

            if channels == 1:
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                rgba[..., 0] = parsed
                rgba[..., 1] = parsed
                rgba[..., 2] = parsed
                rgba[..., 3] = 255
                img = Image.fromarray(rgba, mode="RGBA")

            elif channels == 2:
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                rgba[..., 0] = parsed[..., 0]
                rgba[..., 1] = parsed[..., 1]
                rgba[..., 2] = 0
                rgba[..., 3] = 255
                img = Image.fromarray(rgba, mode="RGBA")

            elif channels == 3:
                img = Image.fromarray(parsed, mode="RGB")

            elif channels == 4:
                img = Image.fromarray(parsed, mode="RGBA")

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # type: ignore
        img.save(filename)

    _MGL_DTYPE_TO_NUMPY: dict[str, Any] = {
        'f1': np.uint8,
        'f2': np.float16,
        'f4': np.float32,
        'u1': np.uint8,
        'u2': np.uint16,
        'u4': np.uint32,
        'i1': np.int8,
        'i2': np.int16,
        'i4': np.int32,
    }

    _CUBE_FACE_NAMES = ["posx", "negx", "posy", "negy", "posz", "negz"]

    def _save_cubemap_face(
        self,
        cube_tex: moderngl.TextureCube,
        face_index: int,
        filename: str,
    ) -> None:
        if not 0 <= face_index < 6:
            raise ValueError("Cubemap face must be in range [0, 5]")

        width, height = cube_tex.size
        channels = cube_tex.components
        texture_dtype = cube_tex.dtype

        raw_bytes = cube_tex.read(face_index)

        np_dtype = self._MGL_DTYPE_TO_NUMPY.get(texture_dtype, np.uint8)
        np_data = np.frombuffer(raw_bytes, dtype=np_dtype)

        if np_dtype in (np.float16, np.float32):
            np_data = (
                np.clip(np_data.astype(np.float32), 0.0, 1.0) * 255.0
            ).astype(np.uint8)
        elif np_dtype != np.uint8:
            info = np.iinfo(np_dtype)
            np_data = (
                (np_data.astype(np.float32) - info.min)
                / (info.max - info.min)
                * 255.0
            ).astype(np.uint8)

        if channels == 1:
            parsed = np_data.reshape((height, width))
            rgba = np.empty((height, width, 4), dtype=np.uint8)
            rgba[..., 0] = parsed
            rgba[..., 1] = parsed
            rgba[..., 2] = parsed
            rgba[..., 3] = 255
            img = Image.fromarray(rgba, mode="RGBA")
        elif channels == 2:
            parsed = np_data.reshape((height, width, 2))
            rgba = np.empty((height, width, 4), dtype=np.uint8)
            rgba[..., 0] = parsed[..., 0]
            rgba[..., 1] = parsed[..., 1]
            rgba[..., 2] = 0
            rgba[..., 3] = 255
            img = Image.fromarray(rgba, mode="RGBA")
        elif channels == 3:
            img = Image.fromarray(
                np_data.reshape((height, width, 3)),
                mode="RGB",
            )
        elif channels == 4:
            img = Image.fromarray(
                np_data.reshape((height, width, 4)),
                mode="RGBA",
            )
        else:
            raise ValueError(
                f"Unsupported channel count for cubemap face: {channels}"
            )

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        img.save(filename)

    def save_image(self, filename: str, attachment: Optional[int] = None):
        def cmd():
            target = self._current_target
            if target is None:
                return

            if isinstance(target, ModernGLCubemapTarget):
                cube_tex = target.cubemap

                if attachment is None:
                    for face in range(6):
                        name = self._CUBE_FACE_NAMES[face]
                        self._save_cubemap_face(
                            cube_tex,
                            face,
                            f"{filename}_{name}.png",
                        )
                else:
                    if not 0 <= attachment < 6:
                        raise ValueError("Cubemap face must be in range [0, 5]")
                    self._save_cubemap_face(
                        cube_tex,
                        attachment,
                        filename + ".png",
                    )
                return

            if attachment is None:
                channels = len(target.color_attachments)  # type: ignore
                for i in range(channels):
                    self._save_attachment_image(
                        target.native_handle(),
                        i,
                        f"{filename}_{i}.png",
                    )
                if target.depth_attachment:
                    self._save_attachment_image(
                        target.native_handle(),
                        -1,
                        f"{filename}_depth.png",
                    )
            else:
                self._save_attachment_image(
                    target.native_handle(),
                    attachment,
                    filename + ".png",
                )

        self._commands.append(cmd)

    def redirect(
        self,
        dst_target: RenderTarget,
        src_attachment: int | str,
        dst_attachment: int | str
    ) -> None:
        def cmd_redirect():
            src_target = self._current_target
            if src_target:
                gfx_device.blit_texture_to_target(
                    src_target, dst_target, src_attachment, dst_attachment
                )

        self._commands.append(cmd_redirect)

    def end_render_pass(self) -> None:
        return

    def end(self) -> None:
        pass

    def execute(self, raise_on_error: bool = False) -> None:
        """
        Run every queued command in order.

        Each command is isolated: a failure is logged (with a full
        traceback when DEBUG_GL is on) and execution continues with the
        next command, so a problem attaching one face can no longer starve
        the rest of the frame. Pass raise_on_error=True if you want a
        single aggregated exception raised after all commands have been
        attempted, while still guaranteeing every command got a chance to
        run.
        """
        errors: list[tuple[int, BaseException]] = []
        for index, cmd in enumerate(self._commands):
            try:
                cmd()
            except Exception as exc:
                errors.append((index, exc))
                system.warn(
                    f"[ModernGLCommandBuffer] command #{index} ({getattr(cmd, '__name__', cmd)}) failed: {exc!r}"
                )
                if DEBUG_GL:
                    traceback.print_exc()

        if raise_on_error and errors:
            raise RuntimeError(
                f"{len(errors)} of {len(self._commands)} command(s) failed during execute(): "
                + "; ".join(f"#{i}: {e!r}" for i, e in errors)
            )


class ModernGLGraphicsDevice(GraphicsDevice):
    def __init__(self):
        super().__init__("MODERNGL")

        if not glfw.init():
            raise RuntimeError("Falha ao inicializar GLFW")

        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)  # type: ignore
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)  # type: ignore
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)  # type: ignore
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)  # type: ignore

        self._dummy_window = glfw.create_window(1, 1, "DummyContextWindow", None, None)  # type: ignore
        glfw.make_context_current(self._dummy_window)  # type: ignore

        platform = glfw.get_platform()
        if platform == glfw.PLATFORM_WAYLAND:
            self.ctx = moderngl.create_context(gl_version=(4, 6), backend="egl", share=True)  # type: ignore
        else:
            self.ctx = moderngl.create_context(gl_version=(4, 6))  # type: ignore

        gl.glEnable(gl.GL_TEXTURE_CUBE_MAP_SEAMLESS)  # type: ignore

        # OPT: cache of wrapper FBOs used by blit_texture_to_target, keyed
        # on the Python texture object itself (never on `.glo`, which can
        # be reused after a texture is deleted). See _get_or_create_wrap_fbo.
        self._blit_fbo_cache: "weakref.WeakKeyDictionary[Any, moderngl.Framebuffer]" = weakref.WeakKeyDictionary()

    def initialize(self):
        if not self.ctx:
            self.ctx = moderngl.create_context(standalone=True)

    def _unwrap_native_texture(self, tex_or_wrapper: Any) -> Any:
        return getattr(tex_or_wrapper, "texture", tex_or_wrapper)

    def _resolve_attachment_texture(
        self, target: RenderTarget, attachment: Union[int, str]
    ) -> moderngl.Texture | moderngl.TextureCube:
        if attachment == "depth":
            tex = target.depth_attachment
            if tex is None:
                raise ValueError(
                    f"RenderTarget '{target}' does not have a depth_texture initialized."
                )
            return self._unwrap_native_texture(tex)
        elif isinstance(attachment, int):
            colors = target.color_attachments
            if not colors or attachment < 0 or attachment >= len(colors):
                raise IndexError(
                    f"Color attachment index {attachment} out of bounds for RenderTarget."
                )
            return self._unwrap_native_texture(colors[attachment])
        else:
            raise ValueError(
                f"Invalid attachment specifier '{attachment}'. Use an integer index or 'depth'."
            )

    def _blit_cube_face(
        self,
        src_cube: moderngl.TextureCube,
        dst_cube: moderngl.TextureCube,
        face: int,
        size: tuple[int, int],
    ) -> None:
        read_fbo = glGenFramebuffers(1)  # type: ignore
        draw_fbo = glGenFramebuffers(1)  # type: ignore
        try:
            glBindFramebuffer(GL_READ_FRAMEBUFFER, read_fbo)  # type: ignore
            glFramebufferTexture2D(
                GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,  # type: ignore
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + face, src_cube.glo, 0  # type: ignore
            )

            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, draw_fbo)  # type: ignore
            glFramebufferTexture2D(
                GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,  # type: ignore
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + face, dst_cube.glo, 0  # type: ignore
            )
            glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])  # type: ignore

            w, h = size
            glBlitFramebuffer(  # type: ignore
                0, 0, w, h,
                0, 0, w, h,
                GL_COLOR_BUFFER_BIT, GL_NEAREST  # type: ignore
            )
            _check_gl_error(f"cube face blit {face}")
        finally:
            glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)  # type: ignore
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)  # type: ignore
            glDeleteFramebuffers(1, [read_fbo])
            glDeleteFramebuffers(1, [draw_fbo])

    def _get_or_create_wrap_fbo(self, texture: Any, is_depth: bool) -> moderngl.Framebuffer:
        """OPT: blit_texture_to_target previously created a brand-new
        native FBO wrapper for the source and destination textures on
        *every single call*, and this path runs at least once per view
        per frame (the final redirect-to-backbuffer step of the pass
        chain). Native FBO create/destroy is not free, and in practice
        the same handful of render-target textures get blitted from/to
        every frame, so caching them removes real per-frame churn.

        Cached on the Python texture *object* rather than on its GL name
        (`.glo`): GL names get reused after a texture is deleted, which
        would otherwise let a stale cached FBO silently point at a
        texture that no longer holds what created it. Keying on object
        identity via WeakKeyDictionary plus a weakref finalizer sidesteps
        that: when the texture wrapper is garbage collected its cache
        entry disappears and its native FBO is released automatically.
        """
        cached = self._blit_fbo_cache.get(texture)
        if cached is not None:
            return cached

        fbo = (
            self.ctx.framebuffer(depth_attachment=texture)
            if is_depth
            else self.ctx.framebuffer(color_attachments=[texture])
        )

        def _release_fbo(_ref: Any, fbo: moderngl.Framebuffer = fbo) -> None:
            try:
                fbo.release()
            except Exception:
                pass

        weakref.finalize(texture, _release_fbo)
        self._blit_fbo_cache[texture] = fbo
        return fbo

    def blit_texture_to_target(
        self,
        src_target: RenderTarget,
        dst_target: RenderTarget,
        src_attachment: Union[int, str] = 0,
        dst_attachment: Union[int, str] = 0,
        src_viewport: Optional[tuple[int, int, int, int]] = None,
        dst_viewport: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        if not self.ctx:
            raise RuntimeError("Context ModernGL não foi inicializado")

        is_src_depth = src_attachment == "depth"
        is_dst_depth = dst_attachment == "depth"
        if is_src_depth != is_dst_depth:
            raise ValueError(
                "Cannot blit between mismatched attachment types (e.g., Color to Depth)."
            )

        if src_target is dst_target and src_attachment == dst_attachment:
            return

        has_src_textures = (
            bool(src_target.depth_attachment)
            if is_src_depth
            else bool(getattr(src_target, "color_attachments", None))
        )
        has_dst_textures = (
            bool(dst_target.depth_attachment)
            if is_dst_depth
            else bool(getattr(dst_target, "color_attachments", None))
        )

        src_native = (
            self._resolve_attachment_texture(src_target, src_attachment)
            if has_src_textures else None
        )
        dst_native = (
            self._resolve_attachment_texture(dst_target, dst_attachment)
            if has_dst_textures else None
        )

        src_is_cube = isinstance(src_native, moderngl.TextureCube)
        dst_is_cube = isinstance(dst_native, moderngl.TextureCube)

        if src_is_cube or dst_is_cube:
            if not (src_is_cube and dst_is_cube):
                raise ValueError(
                    "Blit entre TextureCube e Texture2D não é suportado diretamente "
                    "(especifique a face de origem/destino via um wrapper 2D, se necessário)."
                )
            if src_native.size != dst_native.size:  # type: ignore
                raise ValueError("Cubemaps de tamanhos diferentes não podem ser blitadas diretamente.")

            size = src_native.size  # type: ignore
            for face in range(6):
                self._blit_cube_face(src_native, dst_native, face, size)  # type: ignore
            return

        # OPT: reuse cached wrapper FBOs instead of creating/destroying a
        # pair of native FBOs on every call. See _get_or_create_wrap_fbo.
        if has_src_textures:
            src_fb = self._get_or_create_wrap_fbo(src_native, is_src_depth)
            src_w, src_h = src_native.width, src_native.height  # type: ignore
        else:
            src_fb = src_target.native_handle()
            src_w, src_h = src_target.size

        if has_dst_textures:
            dst_fb = self._get_or_create_wrap_fbo(dst_native, is_dst_depth)
            dst_w, dst_h = dst_native.width, dst_native.height  # type: ignore
        else:
            dst_fb = dst_target.native_handle()
            dst_w, dst_h = dst_target.size

        src_fb.viewport = src_viewport if src_viewport is not None else (0, 0, src_w, src_h)
        dst_fb.viewport = dst_viewport if dst_viewport is not None else (0, 0, dst_w, dst_h)

        self.ctx.copy_framebuffer(dst=dst_fb, src=src_fb)

    def shutdown(self):
        if self.ctx:
            self.ctx.release()
        if self._dummy_window:
            glfw.destroy_window(self._dummy_window)  # type: ignore

    def create_framebuffer(
        self, width: int, height: int, texture: Any = None, dtype: str = "f1"
    ) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer"
            )
        return ModernGLFramebufferTarget(
            self.ctx, width, height, color_formats=[texture] if texture else [4], dtype=dtype
        )

    def create_mrt_framebuffer(
        self,
        width: int,
        height: int,
        color_formats: list[int] | list[Texture2D],
        has_depth: bool = True,
        dtype: str = "f1",
        color_dtypes: Optional[list[Optional[str]]] = None,
    ) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer MRT"
            )
        return ModernGLFramebufferTarget(
            self.ctx,
            width,
            height,
            color_formats=color_formats,
            has_depth=has_depth,
            dtype=dtype,
            color_dtypes=color_dtypes,
        )

    def create_cubemap_framebuffer(self, size: int, color_formats: list[int], components: int, dtype: str = "f1") -> ModernGLCubemap:
        return ModernGLCubemap(size, color_formats, components, dtype)

    def create_vertex_buffer(self, size: int, dynamic: bool = False) -> GPUBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um vertex buffer"
            )
        return ModernGLGPUBuffer(size, dynamic)

    def create_index_buffer(self, size: int, dynamic: bool = False) -> GPUBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um index buffer"
            )
        return ModernGLGPUBuffer(size, dynamic)

    def create_shader_program(self, program: Any) -> GPUShader:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um shader program"
            )

        return ModernGLGPUShader(program)

    def create_vertex_layout(
        self,
        shader: Any,
        vertex_buffer: Optional[GPUBuffer] = None,
        layout_format: Optional[str] = None,
        attributes: Optional[list[str]] = None,
        index_buffer: Optional[GPUBuffer] = None,
    ) -> VertexLayout:
        return ModernGLVertexLayout(layout_format, attributes)

    def create_vertex_layout_primitive(
        self,
        shader: Any,
        vertex_buffer: GPUBuffer,
        layout_format: str,
        attributes: list[str],
        base_vertex: int,
        index_byte_offset: int,
        index_buffer: Optional[GPUBuffer] = None,
    ) -> VertexLayout:
        return ModernGLVertexLayout(layout_format, attributes)

    def create_uniform_buffer(self, size: int) -> GPUBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um uniform buffer"
            )

        return ModernGLGPUBuffer(size, dynamic=False)

    def create_bindless_storage_buffer(self, size_mb: int) -> GPUBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um storage buffer"
            )

        return ModernGLGPUBuffer(size_mb * 1024 * 1024, dynamic=True)

    def create_bindless_texture_buffer(self, size_mb: int) -> GPUBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um texture buffer"
            )

        return ModernGLGPUBuffer(size_mb * 1024 * 1024, dynamic=True)

    def create_texture2d(self, width: int, height: int, format: int = 4, dtype: str = "f1") -> Texture2D:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar uma textura 2D"
            )

        return ModernGLTexture2D(width, height, components=format, dtype=dtype)

    def create_resource_layout(
        self, bindings: list[tuple[int, ResourceType]]
    ) -> ResourceLayout:
        return ModernGLResourceLayout(bindings)

    def create_resource_set(self, layout: ResourceLayout) -> ResourceSet:
        return ModernGLResourceSet(layout)  # type: ignore

    def create_render_pipeline(
        self, descriptor: RenderPipelineDescriptor
    ) -> RenderPipeline:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um pipeline de renderização"
            )
        return ModernGLRenderPipeline(descriptor)

    def create_command_buffer(self) -> CommandBuffer:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um command buffer"
            )
        return ModernGLCommandBuffer(self.ctx)

    def submit(self, command_buffers: list[CommandBuffer]) -> None:
        for cb in command_buffers:
            if isinstance(cb, ModernGLCommandBuffer):
                cb.execute()

    def create_array_framebuffer(self, width: int, height: int, layers: int, dtype: str = "f2", depth_only: bool = True) -> ArrayFramebuffer:
        if not self.ctx:
            raise RuntimeError("Inicialize o contexto ModernGL antes de criar um array framebuffer")
        if not depth_only:
            raise NotImplementedError("create_array_framebuffer currently only supports depth_only=True")
        return ModernGLArrayFramebuffer(width, height, layers, dtype)