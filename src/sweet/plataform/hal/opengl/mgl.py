import moderngl
import glfw
from sweet.plataform.hal.manager import *
from typing import Any, Optional, Callable, cast, Union
from sweet.plataform.hal.manager import Cubemap, RenderTarget
from .introspection import Introspect, Introspection
import numpy as np
from PIL import Image
from OpenGL.GL import (
    glGenFramebuffers, glBindFramebuffer, glDeleteFramebuffers, glBlitFramebuffer,# type: ignore
    glFramebufferTexture2D, glFramebufferTexture, glDrawBuffers, glCheckFramebufferStatus, # type: ignore
    glViewport, glClearColor, glClear, glClearDepth, # type: ignore
    GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_DEPTH_ATTACHMENT, # type: ignore
    GL_FRAMEBUFFER_COMPLETE, GL_TEXTURE_CUBE_MAP_POSITIVE_X, # type: ignore
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, # type: ignore
    GL_READ_FRAMEBUFFER, GL_DRAW_FRAMEBUFFER, GL_NEAREST, # type: ignore
    glGetIntegerv, glGetError, # type: ignore
    GL_DRAW_FRAMEBUFFER_BINDING, GL_VIEWPORT, GL_NO_ERROR, # type: ignore
)

gfx_device: "ModernGLGraphicsDevice"

class ModernGLTexture2D(Texture2D):
    def __init__(self, width: int, height: int, components: int = 4):
        self.ctx = gfx_device.ctx
        self.width = width
        self.height = height
        self.texture: moderngl.Texture = self.ctx.texture((width, height), components)

    def upload_pixels(self, data: Any, width: int, height: int):
        self.texture.write(data)

    def release(self):
        if self.texture:
            self.texture.release()

class ModernGLCubemap(Cubemap):
    def __init__(self, size: int, components: int):
        glfw.make_context_current(gfx_device._dummy_window) # type: ignore
        self.ctx = gfx_device.ctx
        self.size = size
        self.components = components
        self._cubemap = self.ctx.texture_cube(
            size=(size, size),
            components=components,
            dtype='f2'
        )
        self._target = ModernGLGraphicsDevice.create_framebuffer(gfx_device, self.size, self.size, self._cubemap)

    def get_target(self):
        return self._target

    def set_filters(self, *filters: Any):
        self._cubemap.filter = filters

    def release(self):
        self._cubemap.release()

class ModernGLGPUShader(GPUShader):
    def __init__(self, source: Any):
        self.program: moderngl.Program = gfx_device.ctx.program(
            vertex_shader=source.vertex, fragment_shader=source.fragment, geometry_shader=source.geometry
        )
        self._introspection = Introspect.introspect_program(self.program.glo)

    def set_program_location(self, name: str, value: int) -> None:
        self.program[name].value = value # type: ignore

    def get_introspection(self) -> Introspection:
        return self._introspection

    def bind(self):
        pass

class ModernGLFramebufferTarget(RenderTarget):
    def __init__(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        color_formats: list[Any] = [4],
        has_depth: bool = True,
    ):
        self.ctx = ctx
        self._size = (width, height)
        self._color_textures: list[Any] = []
        self._is_cubemap = False

        mgl_color_attachments: list[Any] = []
        target_cubemap: Optional[moderngl.TextureCube] = None

        first_fmt = color_formats[0] if len(color_formats) > 0 else color_formats

        if isinstance(first_fmt, moderngl.TextureCube):
            target_cubemap = first_fmt
            self._is_cubemap = True
        elif hasattr(first_fmt, "texture") and isinstance(getattr(first_fmt, "texture"), moderngl.TextureCube):
            target_cubemap = first_fmt.texture  # type: ignore
            self._is_cubemap = True

        if self._is_cubemap and target_cubemap is not None:
            self._color_textures = [first_fmt]
            # Leave mgl_color_attachments empty so ModernGL creates an unattached FBO shell
        else:
            for fmt in color_formats:
                if isinstance(fmt, int):
                    tex = ModernGLTexture2D(width, height, components=fmt)
                else:
                    tex = cast(ModernGLTexture2D, fmt)
                self._color_textures.append(tex)
                mgl_color_attachments.append(tex.texture)

        self._depth_texture: Optional[ModernGLTexture2D] = None
        mgl_depth_attachment: Optional[moderngl.Texture] = None

        if has_depth:
            depth_mgl_tex = ctx.depth_texture((width, height))
            self._depth_texture = ModernGLTexture2D.__new__(ModernGLTexture2D)
            self._depth_texture.ctx = ctx
            self._depth_texture.width = width
            self._depth_texture.height = height
            self._depth_texture.texture = depth_mgl_tex
            mgl_depth_attachment = depth_mgl_tex

        self.native_handle = ctx.framebuffer(
            color_attachments=mgl_color_attachments,
            depth_attachment=mgl_depth_attachment,
        )

        if self._is_cubemap and target_cubemap is not None:
            self._color_textures = [first_fmt]
            self._depth_texture = None  # cubemap layered não aceita depth 2D — ver _RawCubemapFramebuffer

            self.native_handle = _RawCubemapFramebuffer(
                ctx, width, height, target_cubemap
            )
            return

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def color_textures(self) -> list[Texture2D]:
        return self._color_textures  # type: ignore

    @property
    def depth_texture(self) -> Optional[ModernGLTexture2D]:
        return self._depth_texture

    @property
    def framebuffer(self) -> Any:
        return self.native_handle

    def release(self) -> None:
        self.framebuffer.release()

    def make_current(self):
        glfw.make_context_current(gfx_device._dummy_window) # type: ignore

class ModernGLVertexLayout(VertexLayout):
    def __init__(self, layout_format: Optional[str], attributes: Optional[list[str]]):
        self.format_str = layout_format
        self.attributes = attributes

    def bind(self) -> None:
        pass

    def release(self) -> None:
        pass

class ModernGLGPUBuffer(GPUBuffer):
    def __init__(self, size: int, dynamic: bool = False) -> None:
        self.ctx = gfx_device.ctx
        self._size = size
        self.buffer: moderngl.Buffer = self.ctx.buffer(reserve=size, dynamic=dynamic)

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


class ModernGLResourceSet(ResourceSet):
    def __init__(self, layout: ModernGLResourceLayout):
        self.layout = layout
        self.bound_resources: dict[int, ResourceBinding] = {}

    def update(self, bindings: list[ResourceBinding]) -> None:
        for b in bindings:
            if b.binding_slot not in self.layout.bindings:
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

class _RawCubemapFramebuffer:

    def __init__(self, ctx: moderngl.Context, width: int, height: int,
                 cubemap: moderngl.TextureCube):
        self.ctx = ctx
        self.width = width
        self.height = height
        self.cubemap = cubemap
        self.depth_texture = None  # nunca layered aqui — ver docstring

        self._owner_context_window = gfx_device._dummy_window # type: ignore
        glfw.make_context_current(self._owner_context_window) # type: ignore
        
        self.glo = glGenFramebuffers(1) # type: ignore

        self._bind_raw()
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, cubemap.glo, 0) # type: ignore
        glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError(f"Cubemap framebuffer incompleto: status={status:#x}")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def _bind_raw(self):
        glfw.make_context_current(self._owner_context_window) # type: ignore
        glBindFramebuffer(GL_FRAMEBUFFER, self.glo) # type: ignore

    def use_face(self, face_index: int):
        self._bind_raw()
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
            GL_TEXTURE_CUBE_MAP_POSITIVE_X + face_index, # type: ignore
            self.cubemap.glo, 0
        )
        glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])
        glViewport(0, 0, self.width, self.height)

    def use(self):
        self._bind_raw()
        glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])
        glViewport(0, 0, self.width, self.height)

    def clear(
        self,
        color: tuple[float, ...] = (0.0, 0.0, 0.0, 1.0),
        depth: float = 1.0,
        viewport: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        self._bind_raw()
        if viewport is not None:
            x, y, w, h = viewport
            glViewport(x, y, w, h)
        r, g, b = color[0], color[1], color[2]
        a = color[3] if len(color) > 3 else 1.0
        glClearColor(r, g, b, a)
        glClear(GL_COLOR_BUFFER_BIT)  # sem depth: este FBO nunca tem depth attachment

    def release(self):
        glDeleteFramebuffers(1, [self.glo]) # type: ignore

    @property
    def size(self):
        return self.width, self.height

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
    def color_textures(self) -> list[Texture2D]:
        return []  # type: ignore

    @property
    def depth_texture(self) -> Optional[Texture2D]:
        return None

    @property
    def native_handle(self) -> moderngl.Framebuffer:
        return self.ctx.screen

    @property
    def framebuffer(self) -> moderngl.Framebuffer:
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

        self._vao_cache: dict[
            tuple[int, int, Optional[int], int], moderngl.VertexArray
        ] = {}

    def get_or_create_vao(
        self,
        target_id: int,
        vbo: ModernGLGPUBuffer,
        ibo: Optional[ModernGLGPUBuffer] = None,
        base_vertex: int = 0,
    ) -> moderngl.VertexArray:
        cache_key = (target_id, id(vbo), id(ibo), base_vertex)

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

            # self._vao_cache[cache_key] = self.ctx.vertex_array( # type: ignore
            #     self.program,
            #     [(vbo.buffer, layout.format_str, *layout.attributes)],
            #     index_buffer=index_buffer
            # )

        return self._vao_cache[cache_key]

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
    ) -> None:
        self._current_target = target

        def cmd_begin_pass(
            t: RenderTarget = target,
            vp: Optional[tuple[int, int, int, int]] = viewport,
            cc: tuple[float, float, float] = clear_color,
        ):
            if hasattr(t, "make_current"):
                t.make_current() # type: ignore

            self.ctx.disable(moderngl.DEPTH_TEST)

            fb = t.framebuffer
            w, h = t.size
            effective_vp = vp if vp is not None else (0, 0, w, h)

            if isinstance(fb, _RawCubemapFramebuffer):
                fb.use()
                glViewport(*effective_vp)
                fb.clear(color=cc)
            else:
                fb.use()
                if w > 0 and h > 0:
                    self.ctx.viewport = effective_vp
                fb.clear(color=cc)

        self._commands.append(cmd_begin_pass)

    def set_pipeline(self, pipeline: RenderPipeline) -> None:
        if not isinstance(pipeline, ModernGLRenderPipeline):
            raise TypeError("Pipeline deve ser compatível com a implementação HAL")
        self._current_pipeline = pipeline

        def cmd_set_pipeline():
            pipeline.apply_state()

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
        self, src_texture: Texture2D, location: int
    ) -> None:
        def use():
            src_texture.texture.use(location=location) # type: ignore

        self._commands.append(use)

    def use_target_texture(
        self, src_render_target: RenderTarget, src_attachment: int, location: int
    ) -> None:
        def use():
            if src_attachment == -1:
                src_render_target.framebuffer.depth_attachment.use(location=location)
            else:
                src_render_target.framebuffer.color_attachments[src_attachment].use(location=location)

        self._commands.append(use)

    def set_uniform_value(self, uniform: str, value: bytes):
        pipeline = self._current_pipeline

        def set_uniform():
            if pipeline and uniform in pipeline.program:
                pipeline.program[uniform].write(value)  # type: ignore

        self._commands.append(set_uniform)

    def draw(
        self,
        vertex_count: int,
        instance_count: int = 1,
        first_vertex: int = 0,
        first_instance: int = 0,
    ) -> None:
        pipeline = self._current_pipeline
        vbo = self._current_vbo

        if vbo is None:
            def empty_cmd():
                # vao = self.ctx.vertex_array(pipeline.program, [])  # type: ignore
                # vao.render(mode=pipeline.mode, vertices=vertex_count, instances=instance_count, first=first_vertex)  # type: ignore
                vao = self.ctx.vertex_array(pipeline.program, []) # type: ignore
                vao.render(mode=pipeline.mode, vertices=vertex_count, instances=instance_count, first=first_vertex) # type: ignore
                err = glGetError()
                if err != GL_NO_ERROR:
                    print(f"[GL ERROR after cubemap draw] {err:#x}")

            self._commands.append(empty_cmd)
            return

        def cmd_draw():
            vao = self.ctx.vertex_array(  # type: ignore
                pipeline.program,  # type: ignore
                [(vbo.buffer, pipeline.descriptor.vertex_layout.format_str, *pipeline.descriptor.vertex_layout.attributes)],  # type: ignore
            )
            vao.render(mode=pipeline.mode, vertices=vertex_count, instances=instance_count, first=first_vertex)  # type: ignore

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

    def _save_image(self, fb: RenderTarget, name: str):
        def cmd_save():
            if fb:
                for i in range(len(fb.framebuffer.color_attachments)):
                    self._save_attachment_image(fb.framebuffer, i, str(name) + f"_{i}" + ".png")
                if fb.depth_texture:
                    self._save_attachment_image(fb.framebuffer, -1, str(name) + ".png")

        self._commands.append(cmd_save)

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
        self, cube_tex: moderngl.TextureCube, face_index: int, filename: str
    ) -> None:
        width, height = cube_tex.size
        channels = cube_tex.components
        texture_dtype = cube_tex.dtype

        raw_bytes = cube_tex.read(face_index)

        np_dtype = self._MGL_DTYPE_TO_NUMPY.get(texture_dtype, np.uint8)
        np_data = np.frombuffer(raw_bytes, dtype=np_dtype)

        if np_dtype in (np.float16, np.float32):
            # HDR (ex: skybox com sol > 1.0) -- clip simples só pra visualização;
            # se quiser ver o HDR de verdade, troque por um tonemap aqui.
            np_data = (np.clip(np_data.astype(np.float32), 0.0, 1.0) * 255.0).astype(np.uint8)
        elif np_dtype != np.uint8:
            info = np.iinfo(np_dtype)
            np_data = (
                (np_data.astype(np.float32) - info.min) / (info.max - info.min) * 255.0
            ).astype(np.uint8)

        if channels == 1:
            parsed = np_data.reshape((height, width))
            rgba = np.zeros((height, width, 4), dtype=np.uint8)
            rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = parsed
            rgba[..., 3] = 255
            img = Image.fromarray(rgba, mode="RGBA")
        elif channels == 2:
            parsed = np_data.reshape((height, width, 2))
            rgba = np.zeros((height, width, 4), dtype=np.uint8)
            rgba[..., 0] = parsed[..., 0]
            rgba[..., 1] = parsed[..., 1]
            rgba[..., 3] = 255
            img = Image.fromarray(rgba, mode="RGBA")
        elif channels == 3:
            img = Image.fromarray(np_data.reshape((height, width, 3)), mode="RGB")
        elif channels == 4:
            img = Image.fromarray(np_data.reshape((height, width, 4)), mode="RGBA")
        else:
            raise ValueError(f"Unsupported channel count for cubemap face: {channels}")

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)  # type: ignore
        img.save(filename)

    def save_image(self, filename: str, attachment: Optional[int] = None):
        def cmd():
            target = self._current_target
            if target is None:
                return

            colors = getattr(target, "color_textures", None)
            is_cubemap = bool(colors) and isinstance(colors[0], moderngl.TextureCube)

            if is_cubemap:
                cube_tex = colors[0] # type: ignore
                if attachment is None:
                    for face in range(6):
                        name = self._CUBE_FACE_NAMES[face]
                        self._save_cubemap_face(cube_tex, face, f"{filename}_{name}.png")
                else:
                    self._save_cubemap_face(cube_tex, attachment, filename + ".png")
                return

            if attachment is None:
                channels = len(target.color_textures)  # type: ignore
                for i in range(channels):
                    self._save_attachment_image(target.framebuffer, i, f"{filename}_{i}.png")  # type: ignore
                self._save_attachment_image(target.framebuffer, -1, f"{filename}_depth.png")  # type: ignore
            else:
                self._save_attachment_image(target.framebuffer, attachment, filename + ".png")  # type: ignore

        self._commands.append(cmd)

    def redirect(
        self,
        dst_target: RenderTarget,
        src_attachment: int | str,
        dst_attachment: int | str
    ) -> None:
        def cmd_redirect():
            src_target = self._current_target
            # print(src_target.color_textures, dst_target.color_textures)
            if src_target:
                gfx_device.blit_texture_to_target(
                    src_target, dst_target, src_attachment, dst_attachment
                )

        self._commands.append(cmd_redirect)

    def end_render_pass(self) -> None:
        return

    def end(self) -> None:
        pass

    def execute(self) -> None:
        for cmd in self._commands:
            cmd()


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

        # self.ctx: moderngl.Context = cast(moderngl.Context, moderngl.create_context(gl_version=(4, 6))) # type: ignore

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
            tex = target.depth_texture
            if tex is None:
                raise ValueError(
                    f"RenderTarget '{target}' does not have a depth_texture initialized."
                )
            return self._unwrap_native_texture(tex)
        elif isinstance(attachment, int):
            colors = target.color_textures
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
        read_fbo = glGenFramebuffers(1) # type: ignore
        draw_fbo = glGenFramebuffers(1) # type: ignore
        try:
            glBindFramebuffer(GL_READ_FRAMEBUFFER, read_fbo) # type: ignore
            glFramebufferTexture2D(
                GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, # type: ignore
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + face, src_cube.glo, 0 # type: ignore
            )

            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, draw_fbo) # type: ignore
            glFramebufferTexture2D(
                GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, # type: ignore
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + face, dst_cube.glo, 0 # type: ignore
            )
            glDrawBuffers(1, [GL_COLOR_ATTACHMENT0]) # type: ignore

            w, h = size
            glBlitFramebuffer( # type: ignore
                0, 0, w, h,
                0, 0, w, h,
                GL_COLOR_BUFFER_BIT, GL_NEAREST # type: ignore
            )
        finally:
            glBindFramebuffer(GL_READ_FRAMEBUFFER, 0) # type: ignore
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0) # type: ignore
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
            bool(src_target.depth_texture)
            if is_src_depth
            else bool(getattr(src_target, "color_textures", None))
        )
        has_dst_textures = (
            bool(dst_target.depth_texture)
            if is_dst_depth
            else bool(getattr(dst_target, "color_textures", None))
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
                src_fb = src_target.framebuffer
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
                dst_fb = dst_target.framebuffer
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
        self, width: int, height: int, color_formats: list[int] | list[Texture2D], has_depth: bool = True
    ) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer MRT"
            )
        return ModernGLFramebufferTarget(
            self.ctx, width, height, color_formats=color_formats, has_depth=has_depth
        )

    def create_cubemap(self, size: int, components: int) -> ModernGLCubemap:
        return ModernGLCubemap(size, components)

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
