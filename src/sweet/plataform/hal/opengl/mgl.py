import moderngl
import glfw
from sweet.plataform.hal.manager import *
from typing import Any, Optional, Callable, cast, Union
from sweet.plataform.hal.manager import Cubemap, RenderTarget
from .introspection import Introspect, Introspection
from sweet.core import system
import itertools
import traceback
import numpy as np
from PIL import Image
from OpenGL.GL import (
    GL_TEXTURE_CUBE_MAP, # type: ignore
    GL_TEXTURE_CUBE_MAP_POSITIVE_X, GL_TEXTURE_CUBE_MAP_POSITIVE_Y, GL_TEXTURE_CUBE_MAP_POSITIVE_Z, # type: ignore
    GL_TEXTURE_CUBE_MAP_NEGATIVE_X, GL_TEXTURE_CUBE_MAP_NEGATIVE_Y, GL_TEXTURE_CUBE_MAP_NEGATIVE_Z, # type: ignore
    glGenFramebuffers, glBindFramebuffer, glDeleteFramebuffers, glBlitFramebuffer, # type: ignore
    glFramebufferTexture, glFramebufferTexture2D, glDrawBuffers, GL_DEPTH_BUFFER_BIT, # type: ignore
    GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,  # type: ignore
    GL_FRAMEBUFFER_COMPLETE, glCheckFramebufferStatus,# type: ignore
    GL_COLOR_BUFFER_BIT, GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D,  # type: ignore
    GL_READ_FRAMEBUFFER, GL_DRAW_FRAMEBUFFER, GL_NEAREST,  # type: ignore
    glGetError, GL_NO_ERROR, glViewport, glGenFramebuffers, glBindFramebuffer, glClearColor, glClearDepth, glClear, # type: ignore
)

gfx_device: "ModernGLGraphicsDevice"

# Set to True while debugging to get full tracebacks printed for every
# failed command and a GL error check after framebuffer operations.
# FIX: replaces the previously silent, un-instrumented failure path.
DEBUG_GL = False


def _check_gl_error(context: str) -> None:
    """Best-effort GL error check. Only used when DEBUG_GL is on, since
    glGetError() forces a sync point and shouldn't run in hot loops by
    default."""
    if not DEBUG_GL:
        return
    err = glGetError()
    if err != GL_NO_ERROR: # type: ignore
        system.warn(f"[GL] error {hex(err)} after {context}") # type: ignore


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

    def release(self):
        if self.texture:
            self.texture.release()


class ModernGLCubemap(Cubemap):
    """OpenGL cubemap resource backed by a layered framebuffer.

    Rendering a cubemap is a SINGLE render operation.  The framebuffer is
    layered (glFramebufferTexture), and the geometry shader is responsible
    for routing primitives to layers 0..5 through gl_Layer.

    This deliberately follows the working cubemap renderer rather than
    treating the six faces as six independent 2D render targets.
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

        # The working implementation uses a color-only layered FBO.
        # A normal 2D depth texture cannot be attached to a layered color FBO:
        # populated framebuffer attachments must agree on layered-ness.
        # Keep the HAL cubemap target color-only for the same semantics.
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

    def release(self):
        self._target.release()
        self._cubemap.release()


class ModernGLCubemapTarget(RenderTarget):
    """Layered render target for a cubemap.

    IMPORTANT:
        This target does NOT select one face at a time.

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

        # THIS is the key operation.  Do not replace this with
        # glFramebufferTexture2D: that would attach only one cube face and
        # would make gl_Layer ineffective for the intended layout.
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
        """Bind the complete cubemap as one layered framebuffer.

        ``face_index`` is accepted only for source compatibility with the
        previous HAL API. It is intentionally ignored. Rendering a cubemap
        face-by-face is not the layout used by this target.
        """
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
        # The working implementation is color-only, so depth is deliberately
        # ignored. glClear clears the layered color attachment across all
        # cubemap layers.
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
        dtype: str = "f1"
    ):
        self.ctx = ctx
        self._size = (width, height)
        self._color_textures: list[Any] = []
        self._is_cubemap = False
        self._owns_color_textures: list[bool] = []

        mgl_color_attachments: list[Any] = []

        for fmt in color_formats:
            if isinstance(fmt, int):
                tex = ModernGLTexture2D(width, height, components=fmt, dtype=dtype)
                owns = True
            else:
                tex = cast(ModernGLTexture2D, fmt)
                # FIX: track whether we created this texture or the caller
                # passed one in, so release() doesn't free a texture the
                # caller still owns and may reuse elsewhere.
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
        # FIX: only release color textures we actually own -- a texture
        # passed in by the caller (via color_formats containing a
        # Texture2D instead of an int) is not ours to free.
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
    # FIX: a monotonically increasing counter gives every buffer a stable
    # identity for the pipeline's VAO cache. `id(obj)` is NOT safe for this:
    # once a buffer is garbage collected, Python is free to reuse the same
    # address for an unrelated object, which could make a stale VAO cache
    # entry silently point at a completely different (or freed) GPU buffer.
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
        # FIX: shader programs were never released anywhere in the
        # original file.
        if self.program:
            self.program.release()


class ModernGLResourceSet(ResourceSet):
    def __init__(self, layout: ModernGLResourceLayout):
        self.layout = layout
        self.bound_resources: dict[int, ResourceBinding] = {}

    def _slot_declared(self, slot: int) -> bool:
        # FIX: `self.layout.bindings` may be a dict keyed by slot, or a
        # list/tuple of (slot, ResourceType) pairs -- the original code did
        # `slot not in self.layout.bindings`, which only works for the dict
        # case. Against a list of tuples, an int is never equal to a tuple,
        # so the check would effectively always fail (or always "pass" in
        # the sense of raising every time). This handles both shapes.
        bindings = self.layout.bindings
        if isinstance(bindings, dict): # type: ignore
            return slot in bindings
        try:
            return any(entry[0] == slot for entry in bindings) # type: ignore
        except (TypeError, IndexError):
            # Unknown shape -- fail open rather than incorrectly rejecting
            # every binding.
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

    def make_current(self):
        if self.window and hasattr(self.window, "make_current"):
            self.window.make_current()

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

        # FIX: cache key now uses stable buffer.uid instead of id(vbo)/id(ibo).
        self._vao_cache: dict[
            tuple[int, int, Optional[int], int], moderngl.VertexArray
        ] = {}
        # FIX: a single cached attributeless VAO, reused across every
        # bindless/attributeless draw call instead of allocating a new one
        # per draw (see ModernGLCommandBuffer.draw).
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
                    base_vertex,  # Base vertex offset!
                )

            self._vao_cache[cache_key] = self.ctx.vertex_array(  # type: ignore
                self.program, [buffer_spec], index_buffer=index_buffer
            )

        return self._vao_cache[cache_key]

    def get_or_create_empty_vao(self) -> moderngl.VertexArray:
        if self._empty_vao is None:
            self._empty_vao = self.ctx.vertex_array(self.program, []) # type: ignore
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

        # FIX: front_face (winding order) was never set here, so it kept
        # whatever value a previous pipeline last left in the GL context.
        # This matters a lot for cubemap rendering: per-face view matrices
        # commonly flip effective triangle winding on some faces, and with
        # cull_mode != "none" that can silently discard all geometry on
        # exactly those faces while leaving others untouched -- looking
        # exactly like "some faces never draw." Set explicitly every time.
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
        else:
            self.ctx.disable(moderngl.BLEND)

    def release(self):
        # FIX: previously nothing ever released the VAOs accumulated in
        # _vao_cache -- every unique (target, vbo, ibo, base_vertex)
        # combination leaked a native GL VAO object for the lifetime of the
        # process. Pipelines should call this when they're discarded.
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
    ) -> None:
        """Begin a render pass.

        Cubemaps are rendered as one layered target.  ``face_index`` remains
        in the signature only so older callers do not immediately break, but
        it no longer changes the framebuffer attachment.
        """
        self._current_target = target

        def cmd_begin_pass(
            t: RenderTarget = target,
            vp: Optional[tuple[int, int, int, int]] = viewport,
            cc: tuple[float, float, float] = clear_color,
            face: Optional[int] = face_index,
        ):
            if hasattr(t, "make_current"):
                t.make_current()  # type: ignore

            if isinstance(t, ModernGLCubemapTarget):
                # Bind ONE layered FBO. No face attachment/re-attachment occurs.
                t.use(face)

                w, h = t.size
                effective_vp = vp if vp is not None else (0, 0, w, h)
                glViewport(*effective_vp)
                t.clear(color=cc)
                return

            fb = t.native_handle()
            w, h = t.size
            effective_vp = vp if vp is not None else (0, 0, w, h)

            fb.use()
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
            # The reference cubemap renderer explicitly disables culling and
            # depth testing. More importantly, face selection is performed by
            # the geometry shader, so ordinary per-face raster state must not
            # accidentally discard layers.
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
            if isinstance(src_texture, ModernGLCubemap):
                src_texture._cubemap.use(location=location)  # type: ignore
                # glGenerateMipmap(GL_TEXTURE_2D)

        self._commands.append(use)

    def use_target_texture(
        self,
        src_render_target: RenderTarget,
        src_attachment: int,
        location: int,
    ) -> None:
        def use():
            if isinstance(src_render_target, ModernGLCubemapTarget):
                if src_attachment != 0:
                    raise ValueError(
                        "Cubemap targets currently expose one color attachment at index 0"
                    )
                src_render_target.cubemap.use(location=location)
                return

            native = src_render_target.native_handle()

            if src_attachment == -1:
                depth = native.depth_attachment
                if depth is None:
                    raise ValueError("RenderTarget has no depth attachment")
                depth.use(location=location)
            else:
                colors = native.color_attachments
                if src_attachment < 0 or src_attachment >= len(colors):
                    raise IndexError(
                        f"Color attachment {src_attachment} out of bounds"
                    )
                colors[src_attachment].use(location=location)

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
            # FIX: reuse a single cached attributeless VAO per pipeline
            # instead of allocating a brand new moderngl.VertexArray (a
            # native GL VAO object) on every execute() with no release --
            # this was a genuine per-frame GPU object leak.
            def empty_cmd(p: ModernGLRenderPipeline = pipeline, vc: int = vertex_count,
                          ic: int = instance_count, fv: int = first_vertex):
                vao = p.get_or_create_empty_vao()
                vao.render(mode=p.mode, vertices=vc, instances=ic, first=fv)

            self._commands.append(empty_cmd)
            return

        def cmd_draw(
            p: ModernGLRenderPipeline = pipeline,
            v: ModernGLGPUBuffer = vbo,
            t: Optional[RenderTarget] = target,
            vc: int = vertex_count,
            ic: int = instance_count,
            fv: int = first_vertex,
        ):
            # FIX: also routed through the pipeline's VAO cache (same one
            # draw_indexed uses) instead of creating+leaking a new VAO
            # every single call.
            vao = p.get_or_create_vao(id(t) if t is not None else 0, v, None, base_vertex=0)
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
            vao = p.get_or_create_vao(id(t), v, i, base_vertex=bv)
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
            )

            # Parse buffer into normalized uint8 array regardless of dtype
            if "4" in texture_dtype:
                np_data = np.frombuffer(raw_bytes, dtype=np.float32)
                np_data = (np.clip(np_data, 0.0, 1.0) * 255.0).astype(np.uint8)
            else:
                np_data = np.frombuffer(raw_bytes, dtype=np.uint8)

            # Reshape into (height, width, channels)
            if channels == 1:
                parsed = np_data.reshape((height, width))
            else:
                parsed = np_data.reshape((height, width, channels))

            # Build output image based on channel count
            if channels == 1:
                # Single channel -> (R, R, R, 255)
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                rgba[..., 0] = parsed
                rgba[..., 1] = parsed
                rgba[..., 2] = parsed
                rgba[..., 3] = 255
                img = Image.fromarray(rgba, mode="RGBA")

            elif channels == 2:
                # Two channels -> (R, G, 0, 255)
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
            # Saving HDR data as PNG is only a visualization operation.
            # The actual cubemap remains HDR; this merely maps [0, 1] to 8-bit.
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

        FIX (the main cubemap bug): previously this was a bare loop with no
        exception handling. Several commands in this file can legitimately
        raise (most notably ModernGLCubemapTarget.use() on an incomplete
        framebuffer for a given face). Because commands for all 6 cube
        faces are queued into the *same* list and executed in the *same*
        loop, one raised exception used to unwind out of execute()
        entirely and abort every command still queued after it -- which is
        exactly consistent with the reported symptom of "face 0 clears,
        nothing after it ever runs."

        Each command is now isolated: a failure is logged (with a full
        traceback when DEBUG_GL is on) and execution continues with the
        next command, so a problem attaching one face can no longer starve
        the rest of the frame. Pass raise_on_error=True if you want a
        single aggregated exception raised after all commands have been
        attempted (useful in tests/CI), while still guaranteeing every
        command got a chance to run.
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

        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)  # Keep hidden! # type: ignore
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

        # Só targets com texturas gerenciadas (color_textures/depth_texture
        # de verdade) passam pelo resolve manual de attachment. Targets como
        # a backbuffer da janela (ModernGLWindowTarget, color_textures=[])
        # usam framebuffer/size diretamente, igual antes.
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

        # --- caminho original, 2D normal (cobre também a backbuffer,
        #     que cai em has_*_textures=False e usa framebuffer/size direto) ---
        tmp_src_fb: Optional[moderngl.Framebuffer] = None
        tmp_dst_fb: Optional[moderngl.Framebuffer] = None

        try:
            if has_src_textures:
                tmp_src_fb = (
                    self.ctx.framebuffer(depth_attachment=src_native)
                    if is_src_depth
                    else self.ctx.framebuffer(color_attachments=[src_native])
                )
                src_fb = tmp_src_fb
                src_w, src_h = src_native.width, src_native.height  # type: ignore
            else:
                src_fb = src_target.native_handle()
                src_w, src_h = src_target.size

            if has_dst_textures:
                tmp_dst_fb = (
                    self.ctx.framebuffer(depth_attachment=dst_native)
                    if is_dst_depth
                    else self.ctx.framebuffer(color_attachments=[dst_native])
                )
                dst_fb = tmp_dst_fb
                dst_w, dst_h = dst_native.width, dst_native.height  # type: ignore
            else:
                dst_fb = dst_target.native_handle()
                dst_w, dst_h = dst_target.size

            src_fb.viewport = src_viewport if src_viewport is not None else (0, 0, src_w, src_h)
            dst_fb.viewport = dst_viewport if dst_viewport is not None else (0, 0, dst_w, dst_h)

            self.ctx.copy_framebuffer(dst=dst_fb, src=src_fb)
        finally:
            if tmp_src_fb:
                tmp_src_fb.release()
            if tmp_dst_fb:
                tmp_dst_fb.release()

    def shutdown(self):
        if self.ctx:
            self.ctx.release()
        if self._dummy_window:
            glfw.destroy_window(self._dummy_window)  # type: ignore

    def create_framebuffer(self, width: int, height: int, texture: Any = None) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer"
            )
        return ModernGLFramebufferTarget(self.ctx, width, height, color_formats=[texture] if texture else [4])

    def create_mrt_framebuffer(
        self, width: int, height: int, color_formats: list[int] | list[Texture2D], has_depth: bool = True, dtype: str = "f1"
    ) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer MRT"
            )
        return ModernGLFramebufferTarget(
            self.ctx, width, height, color_formats=color_formats, has_depth=has_depth, dtype=dtype
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

    def create_texture2d(self, width: int, height: int, format: int = 4) -> Texture2D:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar uma textura 2D"
            )

        return ModernGLTexture2D(width, height, components=format)

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