from __future__ import annotations
from sweet.plataform.display.window.window import WindowSurface
from ..upload import UploadManager, GPUMeshSource
from sweet.resources.assets.importer import ImportManager
from ...plataform.hal.manager import *
from .visibility.frustum import FrustumCulling
from .graph.families.surface import Deffered
import struct
from typing import Any, TYPE_CHECKING
import numpy as np
import glm
from PIL import Image
from dataclasses import dataclass, field
from .graph.render_graph import RenderDomain
from pathlib import Path
import moderngl

if TYPE_CHECKING:
    from ...gameplay.view import View

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

class PipelineManager:
    _initialized = False
    gfx_device: GraphicsDevice

    camera_ubo: GPUBuffer
    model_ssbo: GPUBuffer
    global_layout: ResourceLayout
    global_set: ResourceSet
    pipeline: RenderPipeline

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
    def save_mrt_fbo_to_png(
        cls,
        fbo: Any,
        attachment_index: Union[int, str],
        filename: str,
        near: float = 0.1,
        far: float = 100.0,
    ):
        width, height = fbo.size
        is_depth = attachment_index in (-1, "depth")

        if is_depth:
            # 1. Read depth buffer as 32-bit floats
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
            raw_bytes = fbo.read(
                viewport=(0, 0, width, height),
                components=4,
                attachment=int(attachment_index),
            )
            img = Image.frombytes("RGBA", (width, height), raw_bytes)

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        img.save(filename)
        print(
            f"[Debug] Saved FBO {'depth' if is_depth else f'attachment [{attachment_index}]'} -> {filename}"
        )

    @classmethod
    def save_all_mrt_attachments(cls, fbo: Any, prefix: str = "gbuffer"):
        attachment_names = ["albedo", "normal", "depth", "extra"]
        
        for idx, _ in enumerate(fbo.color_attachments):
            name = attachment_names[idx] if idx < len(attachment_names) else f"attachment_{idx}"
            cls.save_mrt_fbo_to_png(fbo, attachment_index=idx, filename=f"{prefix}_{name}.png")

    @classmethod
    def initialize(cls, device: GraphicsDevice):
        cls.gfx_device = device
        cls._graph = Deffered
        cls._initialize_resources()
        FrustumCulling.initialize(device)

    @classmethod
    def get_uniform_value(cls, name: str) -> None | Any:
        return cls._uniform_batch.get(name)

    @classmethod
    def set_uniform_value(cls, name: str, value: Any):
        cls._uniform_batch[name] = value

    @classmethod
    def _initialize_resources(cls):
        cls._graph.build()
        cls._graph.initialize()

        cls._render_passes: list[RenderPass] = []

        position_buffer = UploadManager.get_bindless_buffer("positions").buffer
        normal_buffer = UploadManager.get_bindless_buffer("normals").buffer
        texcoord_buffer = UploadManager.get_bindless_buffer("texcoords").buffer
        indices_buffer = UploadManager.get_bindless_buffer("indices").buffer
        cls.packet_buffer = cls.gfx_device.create_bindless_storage_buffer(4)

        buffer_map: dict[str, GPUBuffer] = {
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
        
        for shader in cls._graph.graph.active_passes:
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
            
            shader_set.update(list(map(lambda x: ResourceBinding(x[0], x[1], buffer_map[x[2]]), resources)))
            shader_set.apply()

            vertex_layout = cls.gfx_device.create_vertex_layout(shader_program)

            pipeline = cls.gfx_device.create_render_pipeline(
                RenderPipelineDescriptor(
                    shader=shader_program,
                    vertex_layout=vertex_layout,
                    depth_test_enable=True,
                    cull_mode="back"
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

            target = cls.gfx_device.create_mrt_framebuffer(1280, 720, output_components, True)

            cls._resources[shader.name] = target
            
            initial_width, initial_height = 1280, 720
            target_cache = {(initial_width, initial_height): target}

            domain = shader.domain

            render_pass = RenderPass(
                pipeline=pipeline,
                resource_set=shader_set,
                uniforms=uniforms,
                resource_map=inputs,
                target=target,
                target_cache=target_cache,
                domain=domain,
                name=shader.name
            )

            cls._render_passes.append(render_pass)

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
    def process(cls, view: View):
        scene = view.get_scene()
        target, win_surface = view.get_target()
        viewport = view.get_viewport()
        view_matrix = view.view
        projection_matrix = view.projection
        
        if view_matrix is None or projection_matrix is None or scene is None or target is None:
            return

        if viewport is None:
            if win_surface:
                viewport = (0, 0, *win_surface.render_target.size)
            elif target:
                viewport = (0, 0, *target.size)
            else:
                viewport = (0, 0, 1280, 720)

        vp_width, vp_height = viewport[2], viewport[3]

        for render_pass in cls._render_passes:
            current_w, current_h = render_pass.target.size
            
            if current_w != vp_width or current_h != vp_height:
                if (vp_width, vp_height) in render_pass.target_cache:
                    render_pass.target = render_pass.target_cache[(vp_width, vp_height)]
                else:
                    total_outputs = len(render_pass.target.color_textures)
                    new_target = cls.gfx_device.create_mrt_framebuffer(
                        vp_width, vp_height, [4 for _ in range(total_outputs)], True
                    )
                    render_pass.target_cache[(vp_width, vp_height)] = new_target
                    render_pass.target = new_target
                    cls._resources[render_pass.name] = new_target
        
        FrustumCulling.init_command_buffers(scene.data_track.size)
        visible = FrustumCulling.run_culling(scene, projection_matrix * view_matrix) # type: ignore

        if visible is None:
            return

        render_obj_buffer = bytearray()
        object_count: int = 0
        max_indices_in_batch = 0
        
        for obj in visible:
            visual = scene.data_track.index_refs.get(int(obj), None)
            if visual and isinstance(visual.source.source_model, GPUMeshSource):
                model = visual.source.source_model
                pos_range = UploadManager.get_bindless_buffer("positions").get_glsl_range(model.positions.buffer_index) # type: ignore
                norm_range = UploadManager.get_bindless_buffer("normals").get_glsl_range(model.normals.buffer_index) # type: ignore
                uv_range = UploadManager.get_bindless_buffer("texcoords").get_glsl_range(model.texcoords.buffer_index) # type: ignore
                idx_range = UploadManager.get_bindless_buffer("indices").get_glsl_range(model.indices.buffer_index) # type: ignore

                max_indices_in_batch = max(max_indices_in_batch, idx_range[1])
                # trs = scene.data_track.transforms[obj]
                parent_obj = scene.data_track.parent_ids[obj]
                parent_trs = scene.data_track.transforms[parent_obj]
                transform = cls.floats_to_mat4(parent_trs)
                packet: list[Any] = []
                packet.extend(glm.value_ptr(transform)[:16]) # type: ignore
                packet.extend(pos_range)
                packet.extend(norm_range)
                packet.extend(uv_range)
                packet.extend(idx_range)

                binary_packet = struct.pack('16f8I', *packet)
                render_obj_buffer.extend(binary_packet)

                object_count += 1

        if object_count == 0 or len(render_obj_buffer) == 0:
            return

        light = scene.get_lights()[0]
        light_view_matrix = light.get_view()
        light_projection_matrix = light.get_projection()

        cls.set_uniform_value("sw_View", view_matrix)
        cls.set_uniform_value("sw_InvView", glm.inverse(view_matrix)) # type: ignore
        cls.set_uniform_value("sw_Projection", projection_matrix)
        cls.set_uniform_value("sw_InvProjection", glm.inverse(projection_matrix)) # type: ignore
        
        cls.set_uniform_value("sw_LightView", light_view_matrix)#glm.lookAt(light_eye, light_center, light_up)) # type: ignore
        cls.set_uniform_value("sw_LightProjection", light_projection_matrix)#glm.perspective(1, 1, 0.1, 30)) # type: ignore

        light_dir = light.direction
        cls.set_uniform_value("sw_LightDirection", struct.pack('3f', light_dir.x, light_dir.y, light_dir.z))
        
        cls.set_uniform_value("sw_ShadowMapSize", struct.pack('2f', vp_width, vp_height))

        cls.set_uniform_value("sw_Resolution", struct.pack('2f', -vp_width, vp_height))
        cls.set_uniform_value("sw_Radius", struct.pack('1f', 0.1))
        cls.set_uniform_value("sw_Bias", struct.pack('1f', 0.025))

        cam_pos = glm.inverse(view_matrix)[3].xyz # type: ignore
        cls.set_uniform_value("sw_CameraPosition", struct.pack('3f', cam_pos.x, cam_pos.y, cam_pos.z)) # type: ignore
        cls.set_uniform_value("sw_AmbientStrength", struct.pack('f', 0.3))
        
        cmd = cls.gfx_device.create_command_buffer()
        cmd.begin()
        if isinstance(win_surface, WindowSurface) and hasattr(win_surface, 'make_current'):
            win_surface.make_current()

        cls.packet_buffer.upload_data(render_obj_buffer)

        for i, render_pass in enumerate(cls._render_passes):
            cmd.begin_render_pass(target=render_pass.target, viewport=viewport, clear_color=(1.0, 0.0, 0.5))
            cmd.set_pipeline(render_pass.pipeline)

            for resource in render_pass.resource_map.values():
                if resource.is_imported:
                    cmd.use_texture(cls._imported_resources[resource.source], location=resource.dest_location)
                else:
                    cmd.use_target_texture(src_render_target=cls._resources[resource.source], src_attachment=resource.source_attachment, location=resource.dest_location)

            for uniform in render_pass.uniforms:
                value = cls.get_uniform_value(uniform.name)
                if not value is None:
                    cmd.set_uniform_value(uniform.name, value)

            cmd.set_resource_set(set_index=0, resource_set=render_pass.resource_set)

            if render_pass.domain == RenderDomain.SCENE:
                cmd.draw(
                    vertex_count=max_indices_in_batch,
                    instance_count=object_count,
                )
            elif render_pass.domain == RenderDomain.SCREEN:
                cmd.draw(
                    vertex_count=3,
                    instance_count=1
                )


            if i + 1 == len(cls._render_passes):
                dest_target = target if win_surface is None else win_surface.render_target
                cmd.redirect(dest_target, 0, 0)
            
            cmd.end_render_pass()

        cmd.end()
        cls.gfx_device.submit([cmd])

        if win_surface:
            win_surface.swap_buffers()