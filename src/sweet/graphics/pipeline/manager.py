from sweet.plataform.display.window.window import WindowSurface
from sweet.graphics.common import MeshBuffer
from ...gameplay.views.view import View
from ...graphics.upload import UploadManager
from ...resources.assets.importer import ImportManager
from ...plataform.hal.manager import (
    GraphicsDevice,
    RenderPipelineDescriptor,
    ResourceBinding,
    ResourceType,
    RenderPipeline,
    ResourceLayout,
    ResourceSet,
    GPUBuffer
)

import glm

def create_trs_matrix(
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0), 
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0), 
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> glm.mat4:
    mat = glm.mat4(1.0)
    mat = glm.translate(mat, glm.vec3(translation)) # type: ignore
    
    if rotation_deg[0] != 0.0:
        mat = glm.rotate(mat, glm.radians(rotation_deg[0]), glm.vec3(1, 0, 0)) # type: ignore
    if rotation_deg[1] != 0.0:
        mat = glm.rotate(mat, glm.radians(rotation_deg[1]), glm.vec3(0, 1, 0)) # type: ignore
    if rotation_deg[2] != 0.0:
        mat = glm.rotate(mat, glm.radians(rotation_deg[2]), glm.vec3(0, 0, 1)) # type: ignore
        
    mat = glm.scale(mat, glm.vec3(scale)) # type: ignore
    return mat # type: ignore

class PipelineManager:
    _initialized = False
    gfx_device: GraphicsDevice

    camera_ubo: GPUBuffer
    model_ssbo: GPUBuffer
    global_layout: ResourceLayout
    global_set: ResourceSet
    pipeline: RenderPipeline

    @classmethod
    def set_graphics_device(cls, device: GraphicsDevice):
        cls.gfx_device = device

    @classmethod
    def initialize_resources(cls, layout_format_sample: str = "3f 3f 2f"):
        if cls._initialized:
            return

        shader_data = ImportManager.load_shaders(r'temp/russo/test.vsh', r'temp/russo/test.fsh')
        upload = UploadManager.upload_shaders(shader_data)
        cls.shader = UploadManager.retrieve_object(upload.key)

        cls.camera_ubo = cls.gfx_device.create_uniform_buffer(size=128)
        
        cls.model_ssbo = cls.gfx_device.create_uniform_buffer(size=100 * 64) 

        cls.global_layout = cls.gfx_device.create_resource_layout([
            (0, ResourceType.UNIFORM_BUFFER),
            (1, ResourceType.STORAGE_BUFFER),
            (2, ResourceType.TEXTURE_2D)
        ])
        cls.global_set = cls.gfx_device.create_resource_set(cls.global_layout)

        fallback_tex = list(UploadManager._gpu_handles.values())[1] # type: ignore

        cls.global_set.update([
            ResourceBinding(0, ResourceType.UNIFORM_BUFFER, cls.camera_ubo),
            ResourceBinding(1, ResourceType.STORAGE_BUFFER, cls.model_ssbo),
            ResourceBinding(2, ResourceType.TEXTURE_2D, fallback_tex)
        ])

        dummy_vbo = cls.gfx_device.create_vertex_buffer(size=1)
        vertex_layout = cls.gfx_device.create_vertex_layout(
            shader=cls.shader,
            vertex_buffer=dummy_vbo,
            layout_format=layout_format_sample,
            attributes=["position", "normal", "texcoord_0"]
        )

        cls.pipeline = cls.gfx_device.create_render_pipeline(
            RenderPipelineDescriptor(
                shader=cls.shader,
                vertex_layout=vertex_layout,
                depth_test_enable=True,
                cull_mode="back"
            )
        )

        cls._initialized = True

    @classmethod
    def process(cls, view: View):
        if not cls._initialized:
            cls.initialize_resources()

        target, win_surface = view.get_target()
        scene = view.get_scene()
        viewport = view.get_viewport()
        view_matrix = view.view
        projection_matrix = view.projection

        if view_matrix is None or projection_matrix is None or scene is None or target is None or viewport is None or win_surface is None:
            return

        # 1. Update Camera UBO
        cls.camera_ubo.upload_data(projection_matrix.to_bytes(), offset=0)
        cls.camera_ubo.upload_data(view_matrix.to_bytes(), offset=64)

        # 2. Begin Command Recording
        cmd = cls.gfx_device.create_command_buffer()
        cmd.begin()

        if isinstance(win_surface, WindowSurface) and hasattr(win_surface, 'make_current'):
            win_surface.make_current()

        cmd.begin_render_pass(target=target, viewport=viewport, clear_color=(1.0, 0.0, 0.5))

        cmd.set_pipeline(cls.pipeline)
        cmd.set_resource_set(set_index=0, resource_set=cls.global_set)

        mesh_id = 0
        for entity in scene.entities:
            for child in entity.flatten_outline:
                mesh_key = child.get_mesh()
                if mesh_key is None:
                    continue

                # Upload transform matrix for this entity (64 bytes per mat4)
                transform = create_trs_matrix(
                    translation=child.transform.position.unp(), # type: ignore
                    rotation_deg=child.transform.rotation.values, # type: ignore
                    scale=child.transform.scale.unp() # type: ignore
                )
                cls.model_ssbo.upload_data(transform.to_bytes(), offset=mesh_id * 64)

                # Retrieve the MeshBuffer returned by your upload code
                mesh_buffer: MeshBuffer = UploadManager.retrieve_object(mesh_key)

                # Bind the shared VBO & EBO ONCE per mesh
                cmd.set_vertex_buffer(slot=0, buffer=mesh_buffer.vbo)
                if mesh_buffer.ebo is not None:
                    cmd.set_index_buffer(buffer=mesh_buffer.ebo)

                # --- LOOP OVER MESH PRIMITIVES ---
                for prim in mesh_buffer.primitives:
                    if prim.index_count > 0:
                        bytes_per_index = getattr(prim, 'index_byte_size', 4)

                        first_index = prim.index_byte_offset // bytes_per_index

                        cmd.draw_indexed(
                            index_count=prim.index_count,
                            instance_count=1,
                            first_index=first_index,
                            base_vertex=prim.base_vertex,
                            first_instance=mesh_id
                        )

                    else:
                        # Non-indexed drawing
                        cmd.draw(
                            vertex_count=prim.vertex_count,
                            instance_count=1,
                            first_vertex=prim.base_vertex,
                            first_instance=mesh_id
                        )

                mesh_id += 1

        cmd.end_render_pass()
        cmd.end()

        # 3. Dispatch to GPU
        cls.gfx_device.submit([cmd])
        
        win_surface.swap_buffers()  # Swap buffers for the window surface if applicable