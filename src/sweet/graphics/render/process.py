from __future__ import annotations
from sweet.plataform.display.window.window import WindowSurface
from ..upload import UploadManager, GPUMeshSource
from sweet.resources.assets.importer import ImportManager
from ...plataform.hal.manager import *
import moderngl
from .visibility.frustum import FrustumCulling
from .graph.families.surface import Deffered
from .graph.families.skybox import SkyBox
import struct
from typing import Any, TYPE_CHECKING
import numpy as np
import math
import glm
from dataclasses import dataclass, field
from .graph.render_graph import RenderDomain, Graph, PassConfig
from pathlib import Path
# from OpenGL import GL

if TYPE_CHECKING:
    from ...gameplay.view import View
    from ...gameplay.skybox import SkyBox as CubeMapBox

@dataclass
class ShaderInput:
    name: str
    type_name: str
    location: int
    is_texture: bool = False
    is_imported: bool = False
    source: str | None = None
    source_attachment: int = 0
    source_mip_level: int = 0

@dataclass
class RenderPass:
    name: str
    pipeline: RenderPipeline
    resource_set: ResourceSet
    inputs: list[ShaderInput]
    target: RenderTarget
    config: PassConfig = field(default_factory=PassConfig)
    output_components: list[int] = field(default_factory=list) # type: ignore
    target_cache: dict[tuple[int, int], tuple[RenderTarget, Any]] = field(default_factory=dict) # type: ignore
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

class CubemapRenderer:
    @staticmethod
    def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray):
        f = target - eye
        f /= np.linalg.norm(f)
        s = np.cross(f, up)
        s /= np.linalg.norm(s)
        u = np.cross(s, f)

        m = np.identity(4, dtype=np.float32)
        m[0, :3] = s
        m[1, :3] = u
        m[2, :3] = -f
        m[:3, 3] = -eye
        return m

    @staticmethod
    def perspective(fov_deg: float, aspect: float, near: float, far: float):
        f = 1.0 / np.tan(np.radians(fov_deg) / 2.0)
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = f / aspect
        m[1, 1] = f
        m[2, 2] = (far + near) / (near - far)
        m[2, 3] = (2.0 * far * near) / (near - far)
        m[3, 2] = -1.0
        return m

    _FACE_DIRECTIONS = [
        (np.array([1, 0, 0]),  np.array([0, -1, 0])),  # +X (Right)
        (np.array([-1, 0, 0]), np.array([0, -1, 0])),  # -X (Left)
        (np.array([0, 1, 0]),  np.array([0, 0, 1])),   # +Y (Top)
        (np.array([0, -1, 0]), np.array([0, 0, -1])),  # -Y (Bottom)
        (np.array([0, 0, 1]),  np.array([0, -1, 0])),  # +Z (Front)
        (np.array([0, 0, -1]), np.array([0, -1, 0])),  # -Z (Back)
    ]

    CUBE_VERTEX_COUNT = 36

    @classmethod
    def build_mvp_matrices(cls):
        proj = cls.perspective(90.0, 1.0, 0.1, 100.0)
        mvps: list[np.ndarray] = []
        for target, up in cls._FACE_DIRECTIONS:
            view = cls.look_at(np.array([0, 0, 0], dtype=np.float32), target, up)
            mvps.append((proj @ view).T)
        return np.array(mvps, dtype=np.float32)

class CascadeShadowRenderer:
    DEFAULT_CASCADE_COUNT = 4
    DEFAULT_LAMBDA = 0.5  # 0 = fully uniform splits, 1 = fully logarithmic
 
    # ------------------------------------------------------------------
    # Split scheme
    # ------------------------------------------------------------------
 
    @classmethod
    def compute_splits(cls, near: float, far: float, count: int,
                        lambda_: float = DEFAULT_LAMBDA) -> list[float]:
        """Practical split scheme (Zhang et al.): blends a log split
        (tight near the camera, where shadow error is most visible) with
        a uniform split (avoids the far cascades from becoming absurdly
        large). Returns `count` far-distances, e.g. for near=0.1, far=100,
        count=4 you get something like [~4, ~14, ~35, 100]."""
        splits = []
        for i in range(1, count + 1):
            p = i / count
            log_split = near * (far / near) ** p
            uniform_split = near + (far - near) * p
            splits.append(lambda_ * log_split + (1.0 - lambda_) * uniform_split)
        return splits
 
    # ------------------------------------------------------------------
    # Frustum corner extraction
    # ------------------------------------------------------------------
 
    @staticmethod
    def _frustum_ray_corners(cam_view: glm.mat4, cam_proj: glm.mat4) -> list[tuple[glm.vec3, glm.vec3]]:
        """Returns the 4 corner rays of the camera frustum, each as a
        (near_point, far_point) pair in world space. Since a perspective
        frustum's edges are straight lines from the eye, any depth along
        the way is a linear interpolation between these two points --
        that's what lets _split_corners() below avoid re-deriving a new
        projection matrix per split."""
        inv_vp = glm.inverse(cam_proj * cam_view)  # type: ignore
        rays = []
        for x in (-1.0, 1.0):
            for y in (-1.0, 1.0):
                near_clip = inv_vp * glm.vec4(x, y, -1.0, 1.0)  # type: ignore
                far_clip = inv_vp * glm.vec4(x, y, 1.0, 1.0)  # type: ignore
                near_pt = glm.vec3(near_clip) / near_clip.w  # type: ignore
                far_pt = glm.vec3(far_clip) / far_clip.w  # type: ignore
                rays.append((near_pt, far_pt))
        return rays  # 4 entries
 
    @staticmethod
    def _split_corners(rays: list[tuple[glm.vec3, glm.vec3]],
                        cam_near: float, cam_far: float,
                        split_near: float, split_far: float) -> list[glm.vec3]:
        t_near = (split_near - cam_near) / (cam_far - cam_near)
        t_far = (split_far - cam_near) / (cam_far - cam_near)
        corners = []
        for near_pt, far_pt in rays:
            corners.append(glm.mix(near_pt, far_pt, t_near))  # type: ignore
            corners.append(glm.mix(near_pt, far_pt, t_far))  # type: ignore
        return corners  # 8 entries
 
    @staticmethod
    def _light_ortho_for_corners(corners: list[glm.vec3], light_dir: glm.vec3,
                                  texel_size: float | None = None,
                                  z_padding: float = 50.0) -> glm.mat4:
        
        center = glm.vec3(0.0)  # type: ignore
        for c in corners:
            center += c
        center /= len(corners)
 
        light_dir_n = glm.normalize(light_dir)  # type: ignore
        up = glm.vec3(0.0, 1.0, 0.0)  # type: ignore
        if abs(glm.dot(light_dir_n, up)) > 0.99:  # type: ignore
            up = glm.vec3(0.0, 0.0, 1.0)  # type: ignore
 
        eye = center - light_dir_n * 500.0
        light_view = glm.lookAt(eye, center, up)  # type: ignore
 
        min_v = glm.vec3(float("inf"))  # type: ignore
        max_v = glm.vec3(float("-inf"))  # type: ignore
        for c in corners:
            lv = light_view * glm.vec4(c, 1.0)  # type: ignore
            min_v = glm.min(min_v, glm.vec3(lv))  # type: ignore
            max_v = glm.max(max_v, glm.vec3(lv))  # type: ignore
 
        min_v.z -= z_padding
        max_v.z += z_padding
 
        if texel_size:
            min_v.x = math.floor(min_v.x / texel_size) * texel_size
            min_v.y = math.floor(min_v.y / texel_size) * texel_size
            max_v.x = math.floor(max_v.x / texel_size) * texel_size
            max_v.y = math.floor(max_v.y / texel_size) * texel_size
 
        # glm view space looks down -Z, so the visible range [min_v.z, max_v.z]
        # (both typically negative) maps to near/far as -max_v.z / -min_v.z.
        light_proj = glm.ortho(min_v.x, max_v.x, min_v.y, max_v.y, -max_v.z, -min_v.z)  # type: ignore
        return light_proj * light_view  # type: ignore
 
    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
 
    @classmethod
    def compute_cascade_matrices(
        cls,
        cam_view: glm.mat4,
        cam_proj: glm.mat4,
        light_dir: glm.vec3,
        cascade_count: int,
        cam_near: float,
        cam_far: float,
        lambda_: float = DEFAULT_LAMBDA,
        shadow_map_resolution: int | None = None,
    ) -> tuple[bytes, list[float]]:
        """Returns:
            vp_bytes: cascade_count view-projection matrices, concatenated,
                      ready to upload as e.g. sw_CascadeMatrices[0].
            split_far_values: the view-space far-distance of each cascade,
                      for sw_CascadeSplits -- the lighting pass uses these
                      to pick which array layer to sample per-pixel.
        """
        splits = cls.compute_splits(cam_near, cam_far, cascade_count, lambda_)
        rays = cls._frustum_ray_corners(cam_view, cam_proj)
 
        vp_bytes = bytearray()
        prev_near = cam_near
        for split_far in splits:
            corners = cls._split_corners(rays, cam_near, cam_far, prev_near, split_far)
 
            texel_size = None
            if shadow_map_resolution:
                # Rough world-units-per-texel estimate for texel snapping.
                # Uses the diagonal of the near-plane corners of this
                # cascade as a stand-in for the ortho extent; good enough
                # to kill shimmer, not meant to be exact.
                span = glm.length(corners[1] - corners[0])  # type: ignore
                texel_size = max(span, 1e-4) / shadow_map_resolution
 
            vp = cls._light_ortho_for_corners(corners, light_dir, texel_size)
            vp_bytes.extend(bytes(vp))  # glm mats are already column-major, matches GLSL layout
            prev_near = split_far
 
        return bytes(vp_bytes), splits

class PipelineManager:
    _initialized = False
    gfx_device: GraphicsDevice

    camera_ubo: GPUBuffer
    model_ssbo: GPUBuffer
    global_layout: ResourceLayout
    global_set: ResourceSet
    pipeline: RenderPipeline
    _graphs: dict[str, list[RenderPass]] = {}

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
    def _apply_mip_config(cls, target: RenderTarget, config: PassConfig):
        if config.mip_levels == 1 or len(target.color_attachments) == 0:
            return
        for i in range(len(target.color_attachments)):
            tex = target.get_color_texture(i)
            if config.mip_levels == -1:
                tex.build_mipmaps(max_level=10)  # full chain — let moderngl use its own default
            else:
                tex.build_mipmaps(max_level=max(config.mip_levels - 1, 0))
            tex.set_filters(moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)

            # gl_tex = tex.texture if hasattr(tex, "texture") else tex

            # print("Texture:", gl_tex)
            # print("Size:", gl_tex.size)
            # print("Components:", gl_tex.components)
            # print("Filter:", gl_tex.filter)
            # GL.glBindTexture(GL.GL_TEXTURE_2D, gl_tex.glo)

            # base = GL.glGetTexParameteriv(
            #     GL.GL_TEXTURE_2D,
            #     GL.GL_TEXTURE_BASE_LEVEL
            # )

            # maximum = GL.glGetTexParameteriv(
            #     GL.GL_TEXTURE_2D,
            #     GL.GL_TEXTURE_MAX_LEVEL
            # )

            # print("BASE LEVEL:", base)
            # print("MAX LEVEL:", maximum)
            # print("MIP LEVEL COUNT:", maximum - base + 1)

    @classmethod
    def _create_pass_target(
        cls, config: PassConfig, width: int, height: int, output_type: str, output_components: list[int]
    ) -> RenderTarget:
        dtype = "f2" if config.hdr else "u1"

        if output_type == "cubemap":
            assert width == height, f"Cubemaps precisam ser quadradas (recebido {width}x{height})."
            cubemap = cls.gfx_device.create_cubemap_framebuffer(width, [4], 4, dtype=dtype)
            return cubemap.get_target()

        elif output_type == "csm":
            array = cls.gfx_device.create_array_framebuffer(
                width, height, config.shadow_cascades, dtype=dtype, depth_only=True
            )
            return array.get_target()
        
        target = cls.gfx_device.create_mrt_framebuffer(
            width, height, output_components, has_depth=config.depth_test or config.depth_write or config.depth_texture, dtype=dtype
        )
        cls._apply_mip_config(target, config)
        return target

    @classmethod
    def _resolve_pass_target(cls, render_pass: RenderPass, width: int, height: int, output_type: str = "2d") -> RenderTarget:
        key = (width, height)
        cached = render_pass.target_cache.get(key)
        if cached is not None:
            return cached[0]

        new_target = cls._create_pass_target(
            render_pass.config, width, height, output_type, render_pass.output_components
        )
        render_pass.target_cache[key] = (new_target, None)
        return new_target

    @staticmethod
    def get_component_sizes(attributes: list[Attribute]) -> list[int]:
        component_map: dict[str, int] = {
            'float': 1,
            'vec2': 2,
            'vec3': 3,
            'vec4': 4,
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
                

            resources = (ssbo_bindings + ubo_bindings)
            resources.sort(key=lambda x: x[0])

            shader_layout = cls.gfx_device.create_resource_layout(list(map(lambda x: (x[0], x[1]), resources)))
            shader_set = cls.gfx_device.create_resource_set(shader_layout)
            
            shader_set.update(list(map(lambda x: ResourceBinding(x[0], x[1], cls.buffer_map[x[2]]), resources)))
            shader_set.apply()

            vertex_layout = cls.gfx_device.create_vertex_layout(shader_program)

            config = shader.config

            pipeline = cls.gfx_device.create_render_pipeline(
                RenderPipelineDescriptor(
                    shader=shader_program,
                    vertex_layout=vertex_layout,
                    depth_test_enable=config.depth_test,
                    depth_write_enable=config.depth_write,   # new — confirm this kwarg exists on the descriptor
                    depth_compare_op=config.depth_compare_op,
                    cull_mode=config.cull_mode,
                )
            )

            TEXTURE_TYPES = {"sampler2D", "samplerCube", "sampler2DShadow", "samplerCubeShadow", "sampler2DArray", "sampler2DArrayShadow"}
            inputs: list[ShaderInput] = []
            for input in introspection.inputs.uniforms:
                is_texture = input.type_name in TEXTURE_TYPES
                dependent = shader.dependencies.get(input.name)

                if dependent is None:
                    shader_input = ShaderInput(name=input.name, type_name=input.type_name, location=input.location, is_texture=is_texture,)
                    if is_texture:
                        shader_input.source = input.name
                        shader_input.is_imported = True
                        shader.program.set_program_location(input.name, input.location) # type: ignore
                    inputs.append(shader_input)
                    continue

                src_name, src_shader, *rest = dependent
                mip_level = rest[0] if rest else 0
                src_introspection = src_shader.program.get_introspection()  # type: ignore

                if src_name[:6] == "depth_":
                    src_output_location = -1
                else:
                    src_output_location = None
                    for output in src_introspection.outputs.targets:
                        if output.name == src_name:
                            src_output_location = output.location
                            break
                    if src_output_location is None:
                        raise ValueError(
                            f"Pass '{shader.name}': dependência '{input.name}' aponta para saída "
                            f"'{src_name}' que não existe em '{src_shader.name}'."
                        )

                if is_texture:
                    shader.program.set_program_location(input.name, input.location)  # type: ignore

                inputs.append(ShaderInput(
                    name=input.name, type_name=input.type_name, location=input.location,
                    is_texture=is_texture, source=src_shader.name,
                    source_attachment=src_output_location, source_mip_level=mip_level,
                ))

            output_locations = introspection.outputs.targets
            output_components = cls.get_component_sizes(output_locations)

            domain = config.domain
            if domain == RenderDomain.LIGHT:
                target_w, target_h = cls.light_map_size
                output_type = "2d"
            elif domain == RenderDomain.CUBEMAP:
                target_w = target_h = cls.DEFAULT_CUBEMAP_SIZE
                output_type = "cubemap"
            elif domain == RenderDomain.CASCADE:
                target_w, target_h = cls.light_map_size#config.cascade_resolution
                output_type = "csm"
            else:
                target_w, target_h = 1280, 720
                output_type = "2d"

            target = cls._create_pass_target(config, target_w, target_h, output_type, output_components)
            cls._resources[shader.name] = target
            target_cache = {(target_w, target_h): (target, None)}

            render_pass = RenderPass(
                pipeline=pipeline, resource_set=shader_set, inputs=inputs, target=target,
                target_cache=target_cache, config=config, output_type=output_type,
                output_components=output_components, name=shader.name,
            )

            render_passes.append(render_pass)

        cls._graphs[graph.name] = render_passes

    @classmethod
    def import_resource(cls, name: str, res: Any):
        cls._imported_resources[name] = res

    @classmethod
    def _initialize_resources(cls):
        position_buffer = UploadManager.get_bindless_buffer("positions").buffer
        normal_buffer = UploadManager.get_bindless_buffer("normals").buffer
        texcoord_buffer = UploadManager.get_bindless_buffer("texcoords").buffer
        indices_buffer = UploadManager.get_bindless_buffer("indices").buffer
        volume_buffer = UploadManager.get_bindless_buffer("volumes").buffer
        cls.packet_buffer = cls.gfx_device.create_bindless_storage_buffer(4)

        cls.light_map_size = (4096, 4096)
        cls.DEFAULT_CUBEMAP_SIZE = 1024

        cls.buffer_map: dict[str, GPUBuffer] = {
            "sw_Positions": position_buffer,
            "sw_Normals": normal_buffer,
            "sw_UVs": texcoord_buffer,
            "sw_Indices": indices_buffer,
            "sw_RenderObjects": cls.packet_buffer,
            "sw_Volumes": volume_buffer,
        }

        # cam_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        # sun_dir = np.normalize([0, 1, 0]) if hasattr(np, 'normalize') else np.array([0.0, 0.7, 0.7]) / np.linalg.norm([0.0, 0.7, 0.7])
        # sun_intensity = [20.0, 20.0, 20.0]
        # sun_color, ambient_color = calculate_sun_and_ambient(cam_pos, sun_dir, sun_intensity)

        cls._uniform_batch: dict[str, Any] = {
            "sw_View": bytearray(),
            "sw_Projection": bytearray(),
            "sw_NearPlane": bytearray(),
            "sw_FarPlane": bytearray(),
            # "sw_LightColor": struct.pack('3f', *sun_color),
            "sw_ShadowMapSize": struct.pack('2f', *cls.light_map_size),
            "sw_Radius": struct.pack('1f', .5),
            "sw_Bias": struct.pack('1f', 0.025),
            "sw_Intensity": struct.pack('1f', 1.0),
            "sw_Power": struct.pack('1f', 1.5),
            "sw_BlurRadius": struct.pack('1i', 4),
            "sw_DepthSharpness": struct.pack('1f', 8.0),
            "sw_NormalSharpness": struct.pack('1f', 8.0),
            "sw_AmbientColor": struct.pack('3f', 0.3, 0.3, 0.3),
            # "sw_SunIntensity": struct.pack('3f', *sun_intensity),
            "sw_SunDirection": struct.pack('3f', 0, 1, 0),
            "sw_Exposure": struct.pack('1f', 1.0),
            "sw_CubemapMVP[0]": CubemapRenderer.build_mvp_matrices().tobytes(),
        }

        cls._resources: dict[str, RenderTarget] = {}
        cls._imported_resources: dict[str, Texture2D] = {}

        texture = cls.gfx_device.create_texture2d(4, 4, 3)
        BASE = Path(__file__).parent
        texture_data = ImportManager.load_texture(BASE / "passes" / "ssao" / "noise.png")
        rgb_image = texture_data.source.convert("RGB") # type: ignore
        texture.upload_pixels(rgb_image.tobytes(), 0, 0, 4, 4) # type: ignore
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
            if render_pass.config.domain == RenderDomain.LIGHT:
                w, h = cls.light_map_size
            elif render_pass.config.domain == RenderDomain.CASCADE:
                w, h = cls.light_map_size
            else:
                w, h = vp_width, vp_height
            pass_targets[render_pass.name] = cls._resolve_pass_target(render_pass, w, h, render_pass.output_type)

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
                
                inv_view = glm.inverse(vdata.view_matrix) # type: ignore
                cls.set_uniform_value("sw_View", vdata.view_matrix)
                cls.set_uniform_value("sw_Projection", vdata.projection_matrix)
                cls.set_uniform_value("sw_InvView", inv_view) # type: ignore
                cls.set_uniform_value("sw_InvProjection", glm.inverse(vdata.projection_matrix)) # type: ignore
                cls.set_uniform_value("sw_Resolution", struct.pack('2f', vp_width, vp_height))

                if vdata.scene and hasattr(vdata.scene, 'get_lights'):
                    lights = vdata.scene.get_lights()
                    if lights:
                        light = lights[0]
                        # cls.set_uniform_value("sw_LightView", light.get_view())
                        # cls.set_uniform_value("sw_LightProjection", light.get_projection())
                        light_dir = light.direction
                        cls.set_uniform_value("sw_LightDirection", struct.pack('3f', light_dir.x, light_dir.y, light_dir.z))

                        if render_pass.config.domain == RenderDomain.CASCADE:
                            cascade_count = render_pass.config.shadow_cascades
                            resolution = cls.light_map_size[0]
                            vp_bytes, splits = CascadeShadowRenderer.compute_cascade_matrices(
                                cam_view=vdata.view_matrix,
                                cam_proj=vdata.projection_matrix,
                                light_dir=light_dir.unp(),
                                cascade_count=cascade_count,
                                cam_near=.1,#view.near,   # <<< TODO: troque por onde quer que sua View guarde o near-plane real
                                cam_far=1000,#view.far,    # <<< TODO: idem para far-plane
                                shadow_map_resolution=resolution,
                            )
                            cls.set_uniform_value("sw_LightViewProjections[0]", vp_bytes)
                            cls.set_uniform_value("sw_CascadeCount", struct.pack("1i", cascade_count))
                            cls.set_uniform_value("sw_CascadeSplits", struct.pack(f"{len(splits)}f", *splits))
                        else:
                            cls.set_uniform_value("sw_LightView", light.get_view())
                            cls.set_uniform_value("sw_LightProjection", light.get_projection())

                cam_pos = inv_view[3].xyz # type: ignore
                cls.set_uniform_value("sw_CameraPosition", struct.pack('3f', cam_pos.x, cam_pos.y, cam_pos.z)) # type: ignore

                if render_pass.config.domain == RenderDomain.LIGHT:
                    pass_viewport = (0, 0, cls.light_map_size[0], cls.light_map_size[1])
                elif render_pass.config.domain == RenderDomain.CASCADE:
                    pass_viewport = (0, 0, cls.light_map_size[0], cls.light_map_size[1])
                else:
                    pass_viewport = vdata.viewport

                cmd.begin_render_pass(target=current_target, viewport=pass_viewport, clear_color=(1.0, 0.0, 0.5))
                cmd.set_pipeline(render_pass.pipeline)

                for shader_input in render_pass.inputs:
                    if not shader_input.is_texture:
                        val = cls.get_uniform_value(shader_input.name)
                        if val is not None:
                            cmd.set_uniform_value(shader_input.name, val)
                        continue

                    if shader_input.is_imported:
                        cmd.use_texture(cls._imported_resources.get(shader_input.source), location=shader_input.location)  # unchanged
                        continue

                    src_target = vdata.pass_targets[shader_input.source]
                    mip_level = shader_input.source_mip_level

                    if mip_level is None: mip_level = 0
                    
                    if mip_level == -1:
                        src_tex = src_target.get_color_texture(max(shader_input.source_attachment, 0))
                        mip_level = src_tex.mip_levels - 1
                        src_tex.build_mipmaps(max_level=mip_level + 5)

                    cmd.use_target_texture(
                        src_render_target=src_target,
                        src_attachment=shader_input.source_attachment,
                        location=shader_input.location,
                        src_mip=mip_level,   # HAL now ignores this for GL state, but keep passing it —
                    )                         # useful for logging/debugging and future use
                    if mip_level != 0:
                        cmd.set_uniform_value(f"{shader_input.name}Lod", struct.pack("1f", float(mip_level + 1)))

                cmd.set_resource_set(set_index=0, resource_set=render_pass.resource_set)

                if render_pass.config.domain in (RenderDomain.SCENE, RenderDomain.LIGHT, RenderDomain.CASCADE):
                    cmd.draw(domain="view", vertex_count=vdata.max_indices_in_batch, instance_count=vdata.object_count)
                elif render_pass.config.domain == RenderDomain.SCREEN:
                    cmd.draw(domain="view", vertex_count=3, instance_count=1)
                elif render_pass.config.domain == RenderDomain.CUBEMAP:
                    cmd.draw(domain="cubemap", vertex_count=CubemapRenderer.CUBE_VERTEX_COUNT, instance_count=1)

                # if not hasattr(cls, "k"):
                #     cls.k = 0
                # if cls.k >= 50 and render_pass.name == "VolumetricFogPass":
                # if render_pass.name in ["ShadowPass"]:#["SkyPas;zs", "TonemapPass", "LuminancePass"]:
                #     cmd.save_image(Path(__file__).parent / "targets" / render_pass.name)
                #     cls.k = 0
                # cls.k += 1

                if pass_idx + 1 == total_passes:
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
        size = cm.resolution # type: ignore
        position = getattr(cm, "position", glm.vec3(0.0))  # type: ignore

        vp_matrices_data = bytearray()
        for direction, up in cls._CUBE_FACE_DIRECTIONS:
            view = glm.lookAt(position, position + direction, up)  # type: ignore
            vp_matrix = cls._CUBE_PROJECTION * view
            vp_matrices_data.extend(bytes(vp_matrix))  # type: ignore

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
            max_indices_in_batch=CubemapRenderer.CUBE_VERTEX_COUNT,
            pass_targets=pass_targets,
        )

    @classmethod
    def process_cubemaps(cls, cubemaps: list[CubeMapBox], graph_name: str = "SkyBox"):
        passes = cls._graphs.get(graph_name)
        if not passes or not cubemaps:
            return

        prepared = [cls._prepare_cubemap_data(cm, passes) for cm in cubemaps]
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