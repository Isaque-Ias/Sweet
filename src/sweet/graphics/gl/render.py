from typing import cast
import glm
import struct
from .common import DrawCall
from ...resources.common import TRS
import numpy as np
from collections import defaultdict
from numpy.typing import NDArray
from .introspection import Introspect, DataBlock
from .shaders import ShaderManager
from ..common import BufferInfo
import moderngl
from ...core.linalg.rotation import RotationModel
from .upload import TextureUploader, GeometryUploader

class ShaderRender:
    _projections: dict[str, NDArray[np.float32]] = {}
    _viewsize: tuple[int, int, int, int] = (0, 0, 0, 0)
    _fov = 70
    built = False
    buffer_map: dict[str, dict[int, BufferInfo]] = {}
    batches: dict[str, dict[str | None, dict[str, list[DrawCall]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list))) # type: ignore
    ubo_data: dict[int, dict[str, dict[str, tuple[int | float, ...] | str]]] = {}
    ssbo_data: dict[int, dict[str, dict[str, tuple[int | float, ...] | str]]] = {}

    @classmethod
    def set_context(cls, ctx: moderngl.Context):
        cls._ctx = ctx
        cls._instance_ssbo = cls._ctx.buffer(reserve=4 * 1024 * 1024)
        cls._camera_ubo = cls._ctx.buffer(reserve=128 + 4 + 4 + 4)
        cls._ctx.enable(moderngl.DEPTH_TEST)
        # cls._ctx.disable(moderngl.CULL_FACE)

    @classmethod
    def set_frame_buffer(cls, frame_buffer: moderngl.Framebuffer | None, depth_test: bool=True, clear_color: tuple[float, float, float, float]=(0, 0, 0, 1)):
        renderer = frame_buffer
        if renderer == None:
            renderer = cls._ctx.screen
        
        renderer.use()
        if depth_test:
            cls._ctx.enable(moderngl.DEPTH_TEST)
        else:
            cls._ctx.disable(moderngl.DEPTH_TEST)
        renderer.clear(*clear_color)

    @classmethod
    def add_ubo_data(cls, binding: int, name: str, data_type: str,  *value: int | float) -> None:
        if cls.ubo_data.get(binding) is None:
            cls.ubo_data[binding] = {}

        cls.ubo_data[binding][name] = {"value": value, "type": data_type}

    @classmethod
    def add_ssbo_data(cls, binding: int, name: str, data_type: str, *value: int | float) -> None:
        if cls.ssbo_data.get(binding) is None:
            cls.ssbo_data[binding] = {}

        cls.ssbo_data[binding][name] = {"value": value, "type": data_type}

    @classmethod
    def add_draw_call(cls, draw: DrawCall) -> None:
        shader = draw.shader_handle
        texture = draw.texture_handle
        model = draw.mesh_handle
        cls.batches[shader][texture][model].append(draw) # type: ignore

    @staticmethod
    def create_model_matrix(transform: TRS, alpha: float):
        x, y, z = transform.position
        w, h, t = transform.scale
        rot_obj = transform.rotation

        rot_obj.convert(RotationModel.QUATERNION)

        v = rot_obj.values
        q = glm.quat(v[0], v[1], v[2], v[3])

        t_matrix = np.array([
            [1.0,   0.0,   0.0,   0.0],
            [0.0,   1.0,   0.0,   0.0],
            [0.0,   0.0,   1.0,   0.0],
            [x, y, z, 1.0]
        ], dtype=np.float32)

        s_matrix = np.array([
            [w,   0.0, 0.0, 0.0],
            [0.0, h,   0.0, 0.0],
            [0.0, 0.0, t,   0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32)

        r_matrix = glm.mat4_cast(q) # type: ignore

        return s_matrix @ r_matrix @ t_matrix

    @classmethod
    def render(cls, alpha: float, view: glm.mat4x4, projection: glm.mat4x4) -> None:
        for shader_name, texture_dict in cls.batches.items():
            prog_info = ShaderManager.get_shader(shader_name)
            if not prog_info: continue
            program = prog_info.program

            for ubo in prog_info.introspection.ubos:
                if cls.buffer_map.get(shader_name) is None:
                    cls.buffer_map[shader_name] = {}

                if cls.buffer_map[shader_name].get(ubo.binding) is None:
                    size = ubo.size
                    cls.buffer_map[shader_name][ubo.binding] = BufferInfo(
                        buffer=cls._ctx.buffer(reserve=size),
                        capacity=size
                    )

                ubo_buffer = cls.buffer_map[shader_name][ubo.binding]

                buffer_data = bytearray()

                for member in ubo.members:
                    var_name = member.name.split(".")[-1]
                    if ubo.name == Introspect.engine_prefix + "Camera":
                        if var_name == Introspect.engine_prefix + "projection":
                            buffer_data.extend(projection.to_bytes())
                        elif var_name == Introspect.engine_prefix + "view":
                            buffer_data.extend(view.to_bytes())
                        elif cls.ubo_data.get(ubo.binding, {}).get(var_name):
                            data_type: str = cls.ubo_data[ubo.binding][var_name]["type"] # type: ignore
                            data_value = cls.ubo_data[ubo.binding][var_name]["value"]
                            buffer_data.extend(struct.pack(data_type, *data_value))
                        continue

                    if cls.ubo_data.get(ubo.binding, {}).get(var_name):
                        data_type: str = cls.ubo_data[ubo.binding][var_name]["type"] # type: ignore
                        data_value = cls.ubo_data[ubo.binding][var_name]["value"]
                        buffer_data.extend(struct.pack(data_type, *data_value))
                
                ubo_buffer.buffer.write(buffer_data)
                ubo_buffer.buffer.bind_to_uniform_block(ubo.binding)
            
            instance_buffer = None
            instance_ssbo = None
            for ssbo in prog_info.introspection.ssbos:
                if ssbo.name == Introspect.engine_prefix + "InstanceBuffer":
                    if cls.buffer_map.get(shader_name) is None:
                        cls.buffer_map[shader_name] = {}

                    if cls.buffer_map[shader_name].get(ssbo.binding) is None:
                        initial_size = ssbo.size
                        cls.buffer_map[shader_name][ssbo.binding] = BufferInfo(
                            buffer=cls._ctx.buffer(reserve=initial_size),
                            capacity=initial_size
                        )

                    instance_buffer = cls.buffer_map[shader_name][ssbo.binding]
                    instance_ssbo = ssbo
                    break

            for texture_id, mesh_dict in texture_dict.items():
                if not texture_id is None:
                    tex = TextureUploader.get_texture(texture_id)
                    if tex:
                        tex.use(location=0) 

                        if Introspect.engine_prefix + "texture" in map(lambda x: x.name, prog_info.introspection.uniforms):
                            program[Introspect.engine_prefix + "texture"].value = 0 # type: ignore

                for mesh_id, objects in mesh_dict.items():
                    mesh = GeometryUploader.get_mesh(mesh_id)
                    if not mesh: continue

                    if mesh.vao.get(shader_name) is None:
                        mesh.vao[shader_name] = GeometryUploader.bind_model(program, mesh)

                    if not instance_buffer is None and not instance_ssbo is None:
                        bytes_per_instance = instance_ssbo.size
                        required_size = bytes_per_instance * len(objects)

                        current_buffer = instance_buffer.buffer
                        current_capacity = instance_buffer.capacity

                        if required_size > current_capacity:
                            new_capacity = current_capacity
                            while new_capacity < required_size:
                                new_capacity *= 2
                            
                            current_buffer.release()
                            current_buffer = cls._ctx.buffer(reserve=new_capacity)
                            
                            instance_buffer.buffer = current_buffer
                            instance_buffer.capacity = new_capacity

                        buffer_data = cls.create_instance_buffer(objects, alpha, instance_ssbo)
                        instance_buffer.buffer.write(buffer_data)
                        instance_buffer.buffer.bind_to_storage_buffer(instance_ssbo.binding)

                    mesh.vao[shader_name].render(mode=moderngl.TRIANGLES, instances=len(objects))

        cls.batches = defaultdict(lambda: defaultdict(lambda: defaultdict(list))) # type: ignore
        
    @classmethod
    def create_instance_buffer(cls, calls: list[DrawCall], alpha: float, ssbo: DataBlock) -> bytearray:
        buffer_data = bytearray()
        atlas_size = TextureUploader.get_atlas_size()

        for obj in calls:
            for member in ssbo.members:
                var_name = member.name.split(".")[-1]
                if var_name == Introspect.engine_prefix + "model":
                    transform = cast(TRS, obj.parameters.get("transform"))
                    model_matrix = cls.create_model_matrix(transform, alpha)
                    matrix_bytes = bytes(glm.value_ptr(model_matrix)) # type: ignore
                    buffer_data.extend(matrix_bytes)
                elif var_name == Introspect.engine_prefix + "UV":
                    texture = obj.parameters.get("transform")
                    if not texture is None:
                        u0 = texture.uv.x / atlas_size
                        v0 = texture.uv.y / atlas_size
                        us = texture.uv.w / atlas_size * 0.999
                        vs = texture.uv.h / atlas_size * 0.999
                        buffer_data.extend(struct.pack('4f', u0, v0, us, vs))
                elif var_name == Introspect.engine_prefix + "color":
                    buffer_data.extend(struct.pack('4f', *cast(list[float], obj.parameters.get("color"))))
                if cls.ubo_data.get(ssbo.binding, {}).get(var_name):
                    data_type: str = cls.ssbo_data[ssbo.binding][var_name]["type"] # type: ignore
                    data_value = cls.ssbo_data[ssbo.binding][var_name]["value"]
                    buffer_data.extend(struct.pack(data_type, *data_value))

        return buffer_data