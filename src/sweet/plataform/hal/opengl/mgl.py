import moderngl
import glfw
from sweet.plataform.hal.manager import *
from typing import Any, Optional, Callable, cast, Union
from sweet.plataform.hal.manager import RenderTarget
from .introspection import Introspect, Introspection

gfx_device: "ModernGLGraphicsDevice"

class ModernGLGPUShader(GPUShader):
    def __init__(self, source: Any):
        self.program: moderngl.Program = gfx_device.ctx.program(
            vertex_shader=source.vertex, fragment_shader=source.fragment
        )
        self._introspection = Introspect.introspect_program(self.program.glo)

    def set_program_location(self, name: str, value: int) -> None:
        self.program[name].value = value # type: ignore

    def get_introspection(self) -> Introspection:
        return self._introspection

    def bind(self):
        pass


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


class ModernGLFramebufferTarget(RenderTarget):
    def __init__(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        color_formats: list[int] = [4],
        has_depth: bool = True,
    ):
        self.ctx = ctx
        self._size = (width, height)
        self._color_textures: list[ModernGLTexture2D] = []

        mgl_color_attachments: list[moderngl.Texture] = []
        for fmt in color_formats:
            tex = ModernGLTexture2D(width, height, components=fmt)
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

        self.native_handle: moderngl.Framebuffer = ctx.framebuffer(
            color_attachments=mgl_color_attachments,
            depth_attachment=mgl_depth_attachment,
        )

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
    def framebuffer(self) -> moderngl.Framebuffer:
        return self.native_handle

    def release(self) -> None:
        self.framebuffer.release()


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
        else:
            self.ctx.disable(moderngl.DEPTH_TEST)

        if self.descriptor.cull_mode != "none":
            self.ctx.enable(moderngl.CULL_FACE)
            self.ctx.cull_face = self.descriptor.cull_mode
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
                t.make_current()  # type: ignore

            self.ctx.disable(moderngl.DEPTH_TEST)

            fb: moderngl.Framebuffer = t.framebuffer  # type: ignore

            fb.use()  # type: ignore
            w, h = t.size
            if w > 0 and h > 0:
                self.ctx.viewport = (0, 0, w, h)

            if vp is not None:
                self.ctx.viewport = vp

            fb.clear(color=cc)  # type: ignore

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
        self, src_render_target: RenderTarget, src_attachment: int, location: int
    ) -> None:
        def use():
            src_render_target.framebuffer.color_attachments[src_attachment].use(
                location=location
            )

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
                vao = self.ctx.vertex_array(pipeline.program, [])  # type: ignore
                vao.render(mode=pipeline.mode, vertices=vertex_count, instances=instance_count, first=first_vertex)  # type: ignore

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
        pass

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

    def _resolve_attachment_texture(
        self, target: RenderTarget, attachment: Union[int, str]
    ) -> moderngl.Texture:
        if attachment == "depth":
            tex = target.depth_texture
            if tex is None:
                raise ValueError(
                    f"RenderTarget '{target}' does not have a depth_texture initialized."
                )
            return tex.texture  # type: ignore
        elif isinstance(attachment, int):
            colors = target.color_textures
            if not colors or attachment < 0 or attachment >= len(colors):
                raise IndexError(
                    f"Color attachment index {attachment} out of bounds for RenderTarget."
                )
            return colors[attachment].texture  # type: ignore
        else:
            raise ValueError(
                f"Invalid attachment specifier '{attachment}'. Use an integer index or 'depth'."
            )

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

        tmp_src_fb: Optional[moderngl.Framebuffer] = None
        if src_target.color_textures or (is_src_depth and src_target.depth_texture):
            src_tex = self._resolve_attachment_texture(src_target, src_attachment)
            tmp_src_fb = (
                self.ctx.framebuffer(depth_attachment=src_tex)
                if is_src_depth
                else self.ctx.framebuffer(color_attachments=[src_tex])
            )
            src_fb = tmp_src_fb
            src_w, src_h = src_tex.width, src_tex.height
        else:
            src_fb = src_target.framebuffer
            src_w, src_h = src_target.size

        tmp_dst_fb: Optional[moderngl.Framebuffer] = None
        if dst_target.color_textures or (is_dst_depth and dst_target.depth_texture):
            dst_tex = self._resolve_attachment_texture(dst_target, dst_attachment)
            tmp_dst_fb = (
                self.ctx.framebuffer(depth_attachment=dst_tex)
                if is_dst_depth
                else self.ctx.framebuffer(color_attachments=[dst_tex])
            )
            dst_fb = tmp_dst_fb
            dst_w, dst_h = dst_tex.width, dst_tex.height
        else:
            dst_fb = dst_target.framebuffer
            dst_w, dst_h = dst_target.size

        src_fb.viewport = (
            src_viewport if src_viewport is not None else (0, 0, src_w, src_h)
        )
        dst_fb.viewport = (
            dst_viewport if dst_viewport is not None else (0, 0, dst_w, dst_h)
        )

        try:
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

    def create_framebuffer(self, width: int, height: int) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer"
            )
        return ModernGLFramebufferTarget(self.ctx, width, height)

    def create_mrt_framebuffer(
        self, width: int, height: int, color_formats: list[int], has_depth: bool = True
    ) -> RenderTarget:
        if not self.ctx:
            raise RuntimeError(
                "Inicialize o contexto ModernGL antes de criar um framebuffer MRT"
            )
        return ModernGLFramebufferTarget(
            self.ctx, width, height, color_formats=color_formats, has_depth=has_depth
        )

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
