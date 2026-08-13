from __future__ import annotations
from sweet.plataform.display.window.window import WindowSurface
from ..upload import UploadManager, GPUMeshSource
from ...plataform.hal.manager import *
from .visibility.frustum import FrustumCulling
from .graph.families.surface import Deffered
import struct
from typing import Any, TYPE_CHECKING
import numpy as np
import glm
from PIL import Image
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from ...gameplay.view import View

@dataclass
class Uniform:
    name: str
    type_name: str
    location: int

@dataclass
class RenderPass:
    pipeline: RenderPipeline
    resource_set: ResourceSet
    uniforms: list[Uniform]
    output_location_map: dict[str, tuple[int, int]]
    target: RenderTarget
    target_cache: dict[tuple[int, int], RenderTarget] = field(default_factory=dict) # type: ignore
    drive: str = "scene"

class PipelineManager:
    _initialized = False
    gfx_device: GraphicsDevice

    camera_ubo: GPUBuffer
    model_ssbo: GPUBuffer
    global_layout: ResourceLayout
    global_set: ResourceSet
    pipeline: RenderPipeline

    @classmethod
    def save_mrt_fbo_to_png(cls, fbo: Any, attachment_index: int, filename: str):
        width, height = fbo.size

        raw_bytes = fbo.read(
            viewport=(0, 0, width, height),
            components=4,
            attachment=attachment_index
        )

        img = Image.frombytes('RGBA', (width, height), raw_bytes)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        img.save(filename)
        print(f"[Debug] Saved FBO attachment [{attachment_index}] -> {filename}")

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
            "u_light_direction": struct.pack('3f', -1, 1, 0),
            "u_light_color": struct.pack('3f', 1, 1, 1),
        }

        for shader in cls._graph.graph.active_passes[:2]:
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

            outputs: dict[str, tuple[int, int]] = {}
            for input in introspection.inputs.uniforms:
                dependent = shader.dependencies.get(input.name)
                if dependent is None:
                    continue
                src_name, src_shader = dependent

                src_output_location = None
                src_introspection = src_shader.program.get_introspection() # type: ignore
                for output in src_introspection.outputs.targets:
                    if output.name == src_name:
                        src_output_location = output.location
                        break

                outputs[input.name] = (input.location, src_output_location) # type: ignore
                if input.type_name == "sampler2D":
                    shader.program.set_program_location(input.name, input.location) # type: ignore

            output_locations = introspection.outputs.targets
            target = cls.gfx_device.create_mrt_framebuffer(1280, 720, [4 for _ in range(len(output_locations))], True)

            initial_width, initial_height = 1280, 720
            target_cache = {(initial_width, initial_height): target}

            drive = "scene" if "sw_RenderObjects" in list(map(lambda x: x[2], ssbo_bindings)) else "screen"

            render_pass = RenderPass(
                pipeline=pipeline,
                resource_set=shader_set,
                uniforms=uniforms,
                output_location_map=outputs,
                target=target,
                target_cache=target_cache,
                drive=drive
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

        cls.set_uniform_value("sw_View", view_matrix)
        cls.set_uniform_value("sw_Projection", projection_matrix)
                
        cmd = cls.gfx_device.create_command_buffer()
        cmd.begin()
        if isinstance(win_surface, WindowSurface) and hasattr(win_surface, 'make_current'):
            win_surface.make_current()

        cls.packet_buffer.upload_data(render_obj_buffer)

        last_target: Optional[RenderTarget] = None

        for i, render_pass in enumerate(cls._render_passes):
            cmd.begin_render_pass(target=render_pass.target, viewport=viewport, clear_color=(1.0, 0.0, 0.5))
            cmd.set_pipeline(render_pass.pipeline)

            if not last_target is None:
                for dst_input_location, src_output_location in render_pass.output_location_map.values():
                    cmd.use_texture(src_render_target=last_target, src_attachment=src_output_location, location=dst_input_location)

            last_target = render_pass.target

            for uniform in render_pass.uniforms:
                value = cls.get_uniform_value(uniform.name)
                if not value is None: 
                    cmd.set_uniform_value(uniform.name, value)

            cmd.set_resource_set(set_index=0, resource_set=render_pass.resource_set)

            if render_pass.drive == "scene":
                cmd.draw(
                    vertex_count=max_indices_in_batch,
                    instance_count=object_count,
                )
            else:
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