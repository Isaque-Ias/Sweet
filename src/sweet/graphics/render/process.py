from __future__ import annotations
from sweet.plataform.display.window.window import WindowSurface
from ..upload import UploadManager, GPUMeshSource
from sweet.resources.assets.importer import ImportManager
from ...plataform.hal.manager import *
from .visibility.frustum import FrustumCulling
from .graph.families.surface import Deffered
from .graph.families.skybox import SkyBox
import struct
from typing import Any, TYPE_CHECKING
import numpy as np
import glm
from dataclasses import dataclass, field
from .graph.render_graph import RenderDomain, Graph
from pathlib import Path
import moderngl

if TYPE_CHECKING:
    from ...gameplay.view import View
    from ...gameplay.skybox import SkyBox as CubeMapBox

@dataclass
class ShaderResource:
    source: str
    source_attachment: int
    dest_location: int
    is_imported: bool

@dataclass
class Uniform:
    name: str
    type_name: str
    location: int

@dataclass
class RenderPass:
    name: str
    pipeline: RenderPipeline
    resource_set: ResourceSet
    uniforms: list[Uniform]
    resource_map: dict[str, ShaderResource]
    target: RenderTarget
    target_cache: dict[tuple[int, int], RenderTarget] = field(default_factory=dict) # type: ignore
    domain: RenderDomain = RenderDomain.SCENE
    output_type: str = "2d"

@dataclass
class ViewPreparedData:
    view: View | None
    scene: Any
    target: Any
    win_surface: Any
    viewport: tuple[int, int, int, int]
    view_matrix: glm.mat4
    projection_matrix: glm.mat4
    visible_objects: np.ndarray | None
    render_obj_buffer: bytearray
    object_count: int
    max_indices_in_batch: int
    pass_targets: dict[str, RenderTarget] = field(default_factory=dict) # type: ignore

class PipelineManager:
    _initialized = False
    gfx_device: GraphicsDevice

    camera_ubo: GPUBuffer
    model_ssbo: GPUBuffer
    global_layout: ResourceLayout
    global_set: ResourceSet
    pipeline: RenderPipeline
    _graphs: dict[str, list[RenderPass]] = {}

    CUBE_VERTEX_COUNT = 36  # 6 faces * 2 tris * 3 vértices, cubo unitário sem index buffer

    _CUBE_FACE_DIRECTIONS = [
        (glm.vec3( 1,  0,  0), glm.vec3(0, -1,  0)),  # +X
        (glm.vec3(-1,  0,  0), glm.vec3(0, -1,  0)),  # -X
        (glm.vec3( 0,  1,  0), glm.vec3(0,  0,  1)),  # +Y
        (glm.vec3( 0, -1,  0), glm.vec3(0,  0, -1)),  # -Y
        (glm.vec3( 0,  0,  1), glm.vec3(0, -1,  0)),  # +Z
        (glm.vec3( 0,  0, -1), glm.vec3(0, -1,  0)),  # -Z
    ]
    _CUBE_PROJECTION = glm.perspective(glm.radians(90.0), 1.0, 0.1, 100.0) # type: ignore

    @classmethod
    def _resolve_pass_target(
        cls, render_pass: RenderPass, width: int, height: int, output_type: str = "2d"
    ) -> RenderTarget:
        key = (width, height)
        cached = render_pass.target_cache.get(key)
        if cached is not None:
            return cached

        if output_type == "cubemap":
            assert width == height, (
                f"Cubemaps precisam ser quadradas (recebido {width}x{height}) "
                f"no pass '{render_pass.name}'."
            )
            cubemap = cls.gfx_device.create_cubemap(width, 4)
            new_target = cubemap.get_target()
        else:
            total_outputs = len(render_pass.target.color_textures)
            new_target = cls.gfx_device.create_mrt_framebuffer(
                width, height, [4] * total_outputs, True
            )

        render_pass.target_cache[key] = new_target
        return new_target

    @staticmethod
    def get_component_sizes(attributes: list[Attribute]) -> list[int]:
        component_map: dict[str, int] = {
            'float': 1,
            'vec2': 2,
            'vec3': 3,
            'vec4': 4,
            # Integer mapping if your types use int/uint variants
            'int': 1, 'ivec2': 2, 'ivec3': 3, 'ivec4': 4,
            'uint': 1, 'uvec2': 2, 'uvec3': 3, 'uvec4': 4,
        }
    
        type_int_map: dict[int, int] = {
            5126: 1,   # float
            35664: 2,  # vec2
            35665: 3,  # vec3
            35666: 4,  # vec4
        }

        components: list[int] = []
        sorted_attrs = sorted(attributes, key=lambda attr: attr.location)
        
        for attr in sorted_attrs:
            if attr.type_int in type_int_map:
                components.append(type_int_map[attr.type_int])
            elif attr.type_name in component_map:
                components.append(component_map[attr.type_name])
            else:
                components.append(4) 
                
        return components

    @classmethod
    def initialize(cls, device: GraphicsDevice):
        cls.gfx_device = device
        cls._graph = SkyBox
        cls._initialize_resources()
        FrustumCulling.initialize(device)

    @classmethod
    def get_uniform_value(cls, name: str) -> None | Any:
        return cls._uniform_batch.get(name)

    @classmethod
    def set_uniform_value(cls, name: str, value: Any):
        cls._uniform_batch[name] = value

    @classmethod
    def _load_graph(cls, graph: Graph):
        graph.build()
        graph.initialize()

        render_passes: list[RenderPass] = []

        for shader in graph.graph.active_passes:
            shader_program: GPUShader = shader.program # type: ignore
            introspection = shader_program.get_introspection()
            ssbos = introspection.inputs.ssbos
            ssbo_bindings: list[tuple[int, ResourceType, str]] = []
            for ssbo in ssbos:
                data = (int(ssbo.binding), ResourceType.STORAGE_BUFFER, ssbo.name)
                ssbo_bindings.append(data)

            ubos = introspection.inputs.ubos
            ubo_bindings: list[tuple[int, ResourceType, str]] = []
            for ubo in ubos:
                data = (int(ubo.binding), ResourceType.UNIFORM_BUFFER, ubo.name)
                ubo_bindings.append(data)
                
            unis = introspection.inputs.uniforms
            uniforms: list[Uniform] = []
            for uni in unis:
                uniform = Uniform(name=uni.name, type_name=uni.type_name, location=uni.location)
                uniforms.append(uniform)

            resources = (ssbo_bindings + ubo_bindings)
            resources.sort(key=lambda x: x[0])

            shader_layout = cls.gfx_device.create_resource_layout(list(map(lambda x: (x[0], x[1]), resources)))
            shader_set = cls.gfx_device.create_resource_set(shader_layout)
            
            shader_set.update(list(map(lambda x: ResourceBinding(x[0], x[1], cls.buffer_map[x[2]]), resources)))
            shader_set.apply()

            vertex_layout = cls.gfx_device.create_vertex_layout(shader_program)

            pipeline = cls.gfx_device.create_render_pipeline(
                RenderPipelineDescriptor(
                    shader=shader_program,
                    vertex_layout=vertex_layout,
                    depth_test_enable=False if shader.name == "SkyPass" else True,
                    depth_compare_op="less_equal",
                    cull_mode="none"
                )
            )

            inputs: dict[str, ShaderResource] = {}

            for input in introspection.inputs.uniforms:
                dependent = shader.dependencies.get(input.name)
                
                if dependent is None:
                    if input.type_name == "sampler2D":
                        inputs[input.name] = ShaderResource(source=input.name, source_attachment=src_output_location, dest_location=input.location, is_imported=True) # type: ignore
                        shader.program.set_program_location(input.name, input.location) # type: ignore

                    continue

                src_name, src_shader = dependent

                src_output_location = None
                src_introspection = src_shader.program.get_introspection() # type: ignore

                if src_name[:6] == "depth_":
                    src_output_location = -1
                    
                for output in src_introspection.outputs.targets:
                    if output.name == src_name:
                        src_output_location = output.location
                        break

                source = src_shader.name
                inputs[input.name] = ShaderResource(source=source, source_attachment=src_output_location, dest_location=input.location, is_imported=False) # type: ignore

                if input.type_name == "sampler2D":
                    shader.program.set_program_location(input.name, input.location) # type: ignore

            output_locations = introspection.outputs.targets
            output_components = cls.get_component_sizes(output_locations)

            domain = shader.domain

            if domain == RenderDomain.LIGHT:
                target_w, target_h = cls.light_map_size
                output_type = "2d"
            elif domain == RenderDomain.CUBEMAP:
                target_w = target_h = cls.DEFAULT_CUBEMAP_SIZE
                output_type = "cubemap"
            else:
                target_w, target_h = 1280, 720
                output_type = "2d"

            if output_type == "cubemap":
                cubemap = cls.gfx_device.create_cubemap(target_w, 4)
                target = cubemap.get_target()
            else:
                target = cls.gfx_device.create_mrt_framebuffer(
                    target_w, target_h, output_components, True
                )

            cls._resources[shader.name] = target

            initial_width, initial_height = target_w, target_h
            target_cache = {(initial_width, initial_height): target}

            render_pass = RenderPass(
                pipeline=pipeline,
                resource_set=shader_set,
                uniforms=uniforms,
                resource_map=inputs,
                target=target,
                target_cache=target_cache,
                domain=domain,
                output_type=output_type,
                name=shader.name
            )

            render_passes.append(render_pass)

        cls._graphs[graph.name] = render_passes

    @classmethod
    def _initialize_resources(cls):
        position_buffer = UploadManager.get_bindless_buffer("positions").buffer
        normal_buffer = UploadManager.get_bindless_buffer("normals").buffer
        texcoord_buffer = UploadManager.get_bindless_buffer("texcoords").buffer
        indices_buffer = UploadManager.get_bindless_buffer("indices").buffer
        cls.packet_buffer = cls.gfx_device.create_bindless_storage_buffer(4)

        cls.light_map_size = (4096, 4096)
        cls.DEFAULT_CUBEMAP_SIZE = 1024

        cls.buffer_map: dict[str, GPUBuffer] = {
            "sw_Positions": position_buffer,
            "sw_Normals": normal_buffer,
            "sw_UVs": texcoord_buffer,
            "sw_Indices": indices_buffer,
            "sw_RenderObjects": cls.packet_buffer,
        }

        cls._uniform_batch: dict[str, Any] = {
            "sw_View": bytearray(),
            "sw_Projection": bytearray(),
            "sw_NearPlane": bytearray(),
            "sw_FarPlane": bytearray(),
            "sw_LightColor": struct.pack('3f', 1, 1, 1),
            "sw_ShadowMapSize": struct.pack('2f', *cls.light_map_size),
            "sw_Radius": struct.pack('1f', .5),
            "sw_Bias": struct.pack('1f', 0.025),
            "sw_Intensity": struct.pack('1f', 1.0),
            "sw_Power": struct.pack('1f', 1.5),
            "sw_BlurRadius": struct.pack('1i', 4),
            "sw_DepthSharpness": struct.pack('1f', 8.0),
            "sw_NormalSharpness": struct.pack('1f', 8.0),
            "sw_AmbientStrength": struct.pack('f', 0.3),
            "sw_SunIntensity": struct.pack('3f', 100, 100, 100),
            "sw_SunDirection": struct.pack('3f', 0, 1, 0),
        }

        cls._resources: dict[str, RenderTarget] = {}
        cls._imported_resources: dict[str, Texture2D] = {}

        texture = cls.gfx_device.create_texture2d(4, 4, 3)
        BASE = Path(__file__).parent
        texture_data = ImportManager.load_texture(BASE / "passes" / "ssao" / "noise.png")
        rgb_image = texture_data.source.convert("RGB") # type: ignore
        texture.upload_pixels(rgb_image.tobytes(), 4, 4) # type: ignore
        texture.texture.repeat_x = True # type: ignore
        texture.texture.repeat_y = True # type: ignore
        texture.texture.filter = (moderngl.NEAREST, moderngl.NEAREST) # type: ignore
        cls._imported_resources["SSAO_Noise"] = texture

        cls._load_graph(Deffered())
        cls._load_graph(SkyBox())

    @staticmethod
    def floats_to_mat4(data: np.ndarray) -> glm.mat4:
        pos = glm.vec3(data[0], data[1], data[2])
        
        qx, qy, qz, qw = data[3], data[4], data[5], data[6]
        rot = glm.quat(qw, qx, qy, qz)
        
        scale = glm.vec3(data[7], data[8], data[9])

        mat_translation = glm.translate(glm.mat4(1.0), pos) # type: ignore
        mat_rotation = glm.mat4_cast(rot) # type: ignore
        mat_scale = glm.scale(glm.mat4(1.0), scale) # type: ignore

        return mat_translation * mat_rotation * mat_scale # type: ignore

    @classmethod
    def _prepare_view_data(cls, view: View, passes: list[RenderPass]) -> ViewPreparedData | None:
        scene = view.get_scene()
        target, win_surface = view.get_target()
        viewport = view.get_viewport()
        view_matrix = view.view
        projection_matrix = view.projection

        if view_matrix is None or projection_matrix is None:
            return None

        if viewport is None:
            if win_surface:
                viewport = (0, 0, *win_surface.render_target.size)
            elif target:
                viewport = (0, 0, *target.size)
            else:
                viewport = (0, 0, 1280, 720)

        vp_width, vp_height = viewport[2], viewport[3]

        FrustumCulling.init_command_buffers(scene.data_track.size)
        visible = FrustumCulling.run_culling(scene, projection_matrix * view_matrix)
        if visible is None:
            return None

        pos_buf = UploadManager.get_bindless_buffer("positions")
        norm_buf = UploadManager.get_bindless_buffer("normals")
        uv_buf = UploadManager.get_bindless_buffer("texcoords")
        idx_buf = UploadManager.get_bindless_buffer("indices")

        render_obj_buffer = bytearray()
        object_count = 0
        max_indices_in_batch = 0

        index_refs = scene.data_track.index_refs
        parent_ids = scene.data_track.parent_ids
        transforms = scene.data_track.transforms

        for obj in visible:
            visual = index_refs.get(int(obj), None)
            if visual and isinstance(visual.source.source_model, GPUMeshSource):
                model = visual.source.source_model
                pos_range = pos_buf.get_glsl_range(model.positions.buffer_index) # type: ignore
                norm_range = norm_buf.get_glsl_range(model.normals.buffer_index) # type: ignore
                uv_range = uv_buf.get_glsl_range(model.texcoords.buffer_index) # type: ignore
                idx_range = idx_buf.get_glsl_range(model.indices.buffer_index) # type: ignore

                max_indices_in_batch = max(max_indices_in_batch, idx_range[1])
                parent_trs = transforms[parent_ids[obj]]
                transform = cls.floats_to_mat4(parent_trs)

                packet: list[Any] = list(glm.value_ptr(transform)[:16]) # type: ignore
                packet.extend(pos_range)
                packet.extend(norm_range)
                packet.extend(uv_range)
                packet.extend(idx_range)

                render_obj_buffer.extend(struct.pack('16f8I', *packet))
                object_count += 1

        if object_count == 0:
            return None

        pass_targets: dict[str, RenderTarget] = {}
        for render_pass in passes:
            if render_pass.domain == RenderDomain.LIGHT:
                w, h = cls.light_map_size
            else:
                w, h = vp_width, vp_height
            pass_targets[render_pass.name] = cls._resolve_pass_target(render_pass, w, h, render_pass.output_type)

        # pass_targets: dict[str, RenderTarget] = {}
        # for render_pass in passes:
        #     if render_pass.domain in [RenderDomain.LIGHT]:
        #         pass_targets[render_pass.name] = render_pass.target_cache[cls.light_map_size]
        #     else:
        #         if (vp_width, vp_height) in render_pass.target_cache:
        #             pass_targets[render_pass.name] = render_pass.target_cache[(vp_width, vp_height)]
        #         else:
        #             total_outputs = len(render_pass.target.color_textures)
        #             new_target = cls.gfx_device.create_mrt_framebuffer(
        #                 vp_width, vp_height, [4] * total_outputs, True
        #             )
        #             render_pass.target_cache[(vp_width, vp_height)] = new_target
        #             pass_targets[render_pass.name] = new_target

        return ViewPreparedData(
            view=view,
            scene=scene,
            target=target,
            win_surface=win_surface,
            viewport=viewport,
            view_matrix=view_matrix,
            projection_matrix=projection_matrix,
            visible_objects=visible,
            render_obj_buffer=render_obj_buffer,
            object_count=object_count,
            max_indices_in_batch=max_indices_in_batch,
            pass_targets=pass_targets
        )

    @classmethod
    def process_views(cls, views: list[View], graph_name: str = "Deffered"):
        passes = cls._graphs.get(graph_name)
        if not passes or not views:
            return

        prepared_views: list[ViewPreparedData] = []
        for view in views:
            vdata = cls._prepare_view_data(view, passes)
            if vdata:
                prepared_views.append(vdata)

        if prepared_views:
            cls._execute_render_passes(passes, prepared_views)

    @classmethod
    def _execute_render_passes(cls, passes: list[RenderPass], prepared_items: list[ViewPreparedData]):
        total_passes = len(passes)

        for pass_idx, render_pass in enumerate(passes):
            cmd = cls.gfx_device.create_command_buffer()
            cmd.begin()

            for vdata in prepared_items:
                current_target = vdata.pass_targets[render_pass.name]

                if isinstance(vdata.win_surface, WindowSurface) and hasattr(vdata.win_surface, 'make_current'):
                    vdata.win_surface.make_current()

                if vdata.render_obj_buffer:
                    cls.packet_buffer.upload_data(vdata.render_obj_buffer)

                vp_width, vp_height = vdata.viewport[2], vdata.viewport[3]
                
                cls.set_uniform_value("sw_View", vdata.view_matrix)
                cls.set_uniform_value("sw_Projection", vdata.projection_matrix)
                cls.set_uniform_value("sw_InvView", glm.inverse(vdata.view_matrix)) # type: ignore
                cls.set_uniform_value("sw_InvProjection", glm.inverse(vdata.projection_matrix)) # type: ignore
                cls.set_uniform_value("sw_Resolution", struct.pack('2f', vp_width, vp_height))

                if vdata.scene and hasattr(vdata.scene, 'get_lights'):
                    lights = vdata.scene.get_lights()
                    if lights:
                        light = lights[0]
                        cls.set_uniform_value("sw_LightView", light.get_view())
                        cls.set_uniform_value("sw_LightProjection", light.get_projection())
                        light_dir = light.direction
                        cls.set_uniform_value("sw_LightDirection", struct.pack('3f', light_dir.x, light_dir.y, light_dir.z))

                cls.set_uniform_value("sw_CameraPosition", struct.pack('3f', 0, 0, 0)) # type: ignore

                if render_pass.domain == RenderDomain.LIGHT:
                    pass_viewport = (0, 0, cls.light_map_size[0], cls.light_map_size[1])
                else:
                    pass_viewport = vdata.viewport

                cmd.begin_render_pass(target=current_target, viewport=pass_viewport, clear_color=(1.0, 0.0, 0.5))
                cmd.set_pipeline(render_pass.pipeline)

                for resource in render_pass.resource_map.values():
                    if resource.is_imported:
                        cmd.use_texture(cls._imported_resources[resource.source], location=resource.dest_location)
                    else:
                        src_target = vdata.pass_targets[resource.source]
                        cmd.use_target_texture(
                            src_render_target=src_target,
                            src_attachment=resource.source_attachment,
                            location=resource.dest_location
                        )

                for uniform in render_pass.uniforms:
                    val = cls.get_uniform_value(uniform.name)
                    if val is not None:
                        cmd.set_uniform_value(uniform.name, val)

                cmd.set_resource_set(set_index=0, resource_set=render_pass.resource_set)

                if render_pass.domain in (RenderDomain.SCENE, RenderDomain.LIGHT):
                    cmd.draw(vertex_count=vdata.max_indices_in_batch, instance_count=vdata.object_count)
                elif render_pass.domain == RenderDomain.SCREEN:
                    cmd.draw(vertex_count=3, instance_count=1)
                elif render_pass.domain == RenderDomain.CUBEMAP:
                    cmd.draw(vertex_count=cls.CUBE_VERTEX_COUNT, instance_count=1)

                # if not hasattr(cls, "k"):
                #     cls.k = 0
                # if cls.k > 10:
                # if render_pass.name == "SkyPass":
                #     cmd.save_image(Path(__file__).parent / "targets" / render_pass.name)
                #     print("saved")
                #     cls.k = 0
                # cls.k += .1

                if pass_idx + 1 == total_passes and render_pass.domain != RenderDomain.CUBEMAP:
                    dest_target = vdata.target if vdata.win_surface is None else vdata.win_surface.render_target
                    if dest_target is not None:
                        cmd.redirect(dest_target, 0, 0)

                cmd.end_render_pass()

            cmd.end()
            cls.gfx_device.submit([cmd])

        for vdata in prepared_items:
            if vdata.win_surface:
                vdata.win_surface.swap_buffers()

    @classmethod
    def _prepare_cubemap_data(cls, cm: CubeMapBox, passes: list[RenderPass]) -> ViewPreparedData:
        size = cm.resolution
        position = getattr(cm, "position", glm.vec3(0.0))  # type: ignore

        vp_matrices_data = bytearray()
        for direction, up in cls._CUBE_FACE_DIRECTIONS:
            view = glm.lookAt(position, position + direction, up)  # type: ignore
            vp_matrix = cls._CUBE_PROJECTION * view
            vp_matrices_data.extend(bytes(vp_matrix))  # type: ignore

        cls.set_uniform_value("sw_ShadowMatrices", vp_matrices_data)
        cls.set_uniform_value("sw_ShadowMatrices[0]", vp_matrices_data)

        pass_targets = {
            render_pass.name: cls._resolve_pass_target(render_pass, size, size, render_pass.output_type)
            for render_pass in passes
        }

        return ViewPreparedData(
            view=None,
            scene=cm.scene,
            target=cm.target,
            win_surface=None,
            viewport=(0, 0, size, size),
            view_matrix=glm.mat4(1.0),
            projection_matrix=cls._CUBE_PROJECTION,
            visible_objects=None,
            render_obj_buffer=bytearray(),
            object_count=1,
            max_indices_in_batch=cls.CUBE_VERTEX_COUNT,
            pass_targets=pass_targets,
        )

    @classmethod
    def process_cubemaps(cls, cubemaps: list[CubeMapBox], graph_name: str = "SkyBox"):
        passes = cls._graphs.get(graph_name)
        if not passes or not cubemaps:
            return

        prepared = [cls._prepare_cubemap_data(cm, passes) for cm in cubemaps]

        import glfw
        glfw.make_context_current(cls.gfx_device._dummy_window)
        
        cls._execute_render_passes(passes, prepared)

    # @classmethod
    # def process_cubemaps(cls, cubemaps: list[CubeMapBox], graph_name: str = "SkyBox"):
    #     passes = cls._graphs.get(graph_name)
    #     if not passes or not cubemaps:
    #         return

    #     cubemap_directions = [
    #         (glm.vec3( 1,  0,  0), glm.vec3(0, -1,  0)),  # +X
    #         (glm.vec3(-1,  0,  0), glm.vec3(0, -1,  0)),  # -X
    #         (glm.vec3( 0,  1,  0), glm.vec3(0,  0,  1)),  # +Y
    #         (glm.vec3( 0, -1,  0), glm.vec3(0,  0, -1)),  # -Y
    #         (glm.vec3( 0,  0,  1), glm.vec3(0, -1,  0)),  # +Z
    #         (glm.vec3( 0,  0, -1), glm.vec3(0, -1,  0)),  # -Z
    #     ]
        
    #     proj_matrix = glm.perspective(glm.radians(90.0), 1.0, 0.1, 100.0) # type: ignore
        
    #     for cm in cubemaps:
    #         position = glm.vec3(0.0)
    #         target_fbo = cm.target
    #         size = (cm.resolution, cm.resolution)
            
    #         vp_matrices_data = bytearray()
    #         for direction, up in cubemap_directions:
    #             view = glm.lookAt(position, position + direction, up) # type: ignore
    #             vp_matrix = proj_matrix * view
    #             vp_matrices_data.extend(bytes(vp_matrix)) # type: ignore

    #         cls.set_uniform_value("sw_ShadowMatrices[0]", vp_matrices_data)

    #         prepared_data = ViewPreparedData(
    #             view=None,
    #             scene=cm.scene,
    #             target=target_fbo,
    #             win_surface=None,
    #             viewport=(0, 0, size[0], size[1]),
    #             view_matrix=glm.mat4(1.0),
    #             projection_matrix=proj_matrix,
    #             visible_objects=None,
    #             render_obj_buffer=bytearray(),
    #             object_count=1,
    #             max_indices_in_batch=36,
    #             pass_targets={p.name: target_fbo for p in passes}
    #         )

    #         cls._execute_render_passes(passes, [prepared_data])