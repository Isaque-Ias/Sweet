from ctypes import create_string_buffer
import numpy as np
import OpenGL.GL as gl
from ..manager import Attribute, ResourceOutputs, ResourceInputs, Introspection, DataBlock

class Introspect:
    _GL_TYPE_MAPPING: dict[int, tuple[str, int]] = {
        # Floats / Vectors
        gl.GL_FLOAT: ("float", 4), # type: ignore
        gl.GL_FLOAT_VEC2: ("vec2", 8), # type: ignore
        gl.GL_FLOAT_VEC3: ("vec3", 12), # type: ignore
        gl.GL_FLOAT_VEC4: ("vec4", 16), # type: ignore
        
        # Ints / Vectors
        gl.GL_INT: ("int", 4), # type: ignore
        gl.GL_INT_VEC2: ("ivec2", 8), # type: ignore
        gl.GL_INT_VEC3: ("ivec3", 12), # type: ignore
        gl.GL_INT_VEC4: ("ivec4", 16), # type: ignore
        
        # Unsigned Ints / Vectors
        gl.GL_UNSIGNED_INT: ("uint", 4), # type: ignore
        gl.GL_UNSIGNED_INT_VEC2: ("uvec2", 8), # type: ignore
        gl.GL_UNSIGNED_INT_VEC3: ("uvec3", 12), # type: ignore
        gl.GL_UNSIGNED_INT_VEC4: ("uvec4", 16), # type: ignore
        
        # Bools
        gl.GL_BOOL: ("bool", 4), # type: ignore
        gl.GL_BOOL_VEC2: ("bvec2", 8), # type: ignore
        gl.GL_BOOL_VEC3: ("bvec3", 12), # type: ignore
        gl.GL_BOOL_VEC4: ("bvec4", 16), # type: ignore
        
        # Matrices
        gl.GL_FLOAT_MAT2: ("mat2", 16), # type: ignore
        gl.GL_FLOAT_MAT3: ("mat3", 36), # type: ignore
        gl.GL_FLOAT_MAT4: ("mat4", 64), # type: ignore
        gl.GL_FLOAT_MAT2x3: ("mat2x3", 24), # type: ignore
        gl.GL_FLOAT_MAT2x4: ("mat2x4", 32), # type: ignore
        gl.GL_FLOAT_MAT3x2: ("mat3x2", 24), # type: ignore
        gl.GL_FLOAT_MAT3x4: ("mat3x4", 48), # type: ignore
        gl.GL_FLOAT_MAT4x2: ("mat4x2", 32), # type: ignore
        gl.GL_FLOAT_MAT4x3: ("mat4x3", 48), # type: ignore
        
        # 2D / Cube Samplers
        gl.GL_SAMPLER_1D: ("sampler1D", 4), # type: ignore
        gl.GL_SAMPLER_2D: ("sampler2D", 4), # type: ignore
        gl.GL_SAMPLER_3D: ("sampler3D", 4), # type: ignore
        gl.GL_SAMPLER_CUBE: ("samplerCube", 4), # type: ignore
        gl.GL_SAMPLER_1D_SHADOW: ("sampler1DShadow", 4), # type: ignore
        gl.GL_SAMPLER_2D_SHADOW: ("sampler2DShadow", 4), # type: ignore
        
        # Array & Multisample Samplers
        gl.GL_SAMPLER_1D_ARRAY: ("sampler1DArray", 4), # type: ignore
        gl.GL_SAMPLER_2D_ARRAY: ("sampler2DArray", 4), # type: ignore
        gl.GL_SAMPLER_1D_ARRAY_SHADOW: ("sampler1DArrayShadow", 4), # type: ignore
        gl.GL_SAMPLER_2D_ARRAY_SHADOW: ("sampler2DArrayShadow", 4), # type: ignore
        gl.GL_SAMPLER_2D_MULTISAMPLE: ("sampler2DMS", 4), # type: ignore
        gl.GL_SAMPLER_2D_MULTISAMPLE_ARRAY: ("sampler2DMSArray", 4), # type: ignore
        gl.GL_SAMPLER_CUBE_SHADOW: ("samplerCubeShadow", 4), # type: ignore

        # Integer Samplers (I-Samplers)
        gl.GL_INT_SAMPLER_1D: ("isampler1D", 4), # type: ignore
        gl.GL_INT_SAMPLER_2D: ("isampler2D", 4), # type: ignore
        gl.GL_INT_SAMPLER_3D: ("isampler3D", 4), # type: ignore
        gl.GL_INT_SAMPLER_CUBE: ("isamplerCube", 4), # type: ignore
        gl.GL_INT_SAMPLER_1D_ARRAY: ("isampler1DArray", 4), # type: ignore
        gl.GL_INT_SAMPLER_2D_ARRAY: ("isampler2DArray", 4), # type: ignore
        gl.GL_INT_SAMPLER_2D_MULTISAMPLE: ("isampler2DMS", 4), # type: ignore
        gl.GL_INT_SAMPLER_2D_MULTISAMPLE_ARRAY: ("isampler2DMSArray", 4), # type: ignore

        # Unsigned Integer Samplers (U-Samplers)
        gl.GL_UNSIGNED_INT_SAMPLER_1D: ("usampler1D", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_2D: ("usampler2D", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_3D: ("usampler3D", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_CUBE: ("usamplerCube", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_1D_ARRAY: ("usampler1DArray", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_2D_ARRAY: ("usampler2DArray", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_2D_MULTISAMPLE: ("usampler2DMS", 4), # type: ignore
        gl.GL_UNSIGNED_INT_SAMPLER_2D_MULTISAMPLE_ARRAY: ("usampler2DMSArray", 4) # type: ignore
    }

    @classmethod
    def get_type_info(cls, gl_type: int) -> tuple[str, int]:
        return cls._GL_TYPE_MAPPING.get(gl_type, (f"UNKNOWN_TYPE_(0x{gl_type:X})", 0)) # type: ignore

    @staticmethod
    def get_resource_name(program: int, interface_type: int, index: int) -> str:
        length = np.array([0], dtype=np.int32)
        gl.glGetProgramResourceiv(program, interface_type, index, 1, [gl.GL_NAME_LENGTH], 1, None, length) # type: ignore
        
        if length[0] <= 1:
            return ""

        name_buf = create_string_buffer(int(length[0]))
        gl.glGetProgramResourceName(program, interface_type, index, length[0], None, name_buf)
        return name_buf.value.decode('utf-8')

    @classmethod
    def create_attribute(cls, program_id: int, interface_type: int, index: int) -> Attribute:
        name = cls.get_resource_name(program_id, interface_type, index)

        props = [gl.GL_LOCATION, gl.GL_TYPE, gl.GL_ARRAY_SIZE, gl.GL_BLOCK_INDEX] # type: ignore
        
        if interface_type in (gl.GL_PROGRAM_INPUT, gl.GL_PROGRAM_OUTPUT): # type: ignore
            props = [gl.GL_LOCATION, gl.GL_TYPE, gl.GL_ARRAY_SIZE] # type: ignore
            
        elif interface_type == gl.GL_BUFFER_VARIABLE: # type: ignore
            props = [gl.GL_TYPE, gl.GL_ARRAY_SIZE] # type: ignore

        else:
            props = [gl.GL_LOCATION, gl.GL_TYPE, gl.GL_ARRAY_SIZE, gl.GL_BLOCK_INDEX] # type: ignore

        num_props = len(props)
        values = np.array([0] * num_props, dtype=np.int32)
        gl.glGetProgramResourceiv(program_id, interface_type, index, num_props, props, num_props, None, values)

        location_or_binding = 0
        gl_type = 0
        length = 1
        block_index = -1

        if interface_type in (gl.GL_PROGRAM_INPUT, gl.GL_PROGRAM_OUTPUT): # type: ignore
            location_or_binding = int(values[0])
            gl_type = int(values[1])
            length = int(values[2])
        elif interface_type == gl.GL_BUFFER_VARIABLE: # type: ignore
            gl_type = int(values[0])
            length = int(values[1])
        else:
            location_or_binding = int(values[0])
            gl_type = int(values[1])
            length = int(values[2])
            block_index = int(values[3])

        _, base_size = cls.get_type_info(gl_type)
        type_name = gl_type

        is_in_block = (interface_type == gl.GL_UNIFORM and block_index != -1) or (interface_type == gl.GL_BUFFER_VARIABLE) # type: ignore
        final_size = base_size * length

        if is_in_block:
            stride_props = [gl.GL_ARRAY_STRIDE, gl.GL_MATRIX_STRIDE] # type: ignore
            stride_values = np.array([0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, interface_type, index, 2, stride_props, 2, None, stride_values)
            
            array_stride = int(stride_values[0])
            matrix_stride = int(stride_values[1])

            if matrix_stride > 0:
                num_columns = 4
                if gl_type == gl.GL_FLOAT_MAT3: # type: ignore
                    num_columns = 3
                elif gl_type == gl.GL_FLOAT_MAT2: # type: ignore
                    num_columns = 2
                
                if length > 1 and array_stride > 0:
                    final_size = array_stride * length
                else:
                    final_size = matrix_stride * num_columns
            elif length > 1 and array_stride > 0:
                final_size = array_stride * length

        return Attribute(
            name=name, 
            location=location_or_binding, 
            size=final_size, 
            type_int=type_name, 
            type_name=cls._GL_TYPE_MAPPING[type_name][0], 
            length=length
        )

    @classmethod
    def introspect_targets(cls, program_id: int) -> list[Attribute]:
        targets: list[Attribute] = []
        num_outputs = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_PROGRAM_OUTPUT, gl.GL_ACTIVE_RESOURCES, num_outputs) # type: ignore
        
        for i in range(num_outputs[0]):
            attribute = cls.create_attribute(program_id, gl.GL_PROGRAM_OUTPUT, i) # type: ignore
            
            if attribute.location == -1:
                continue
                
            targets.append(attribute)
        
        targets.sort(key=lambda x: x.location)

        return targets

    @classmethod
    def introspect_layout(cls, program_id: int) -> list[Attribute]:
        layout: list[Attribute] = []

        num_inputs = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_PROGRAM_INPUT, gl.GL_ACTIVE_RESOURCES, num_inputs) # type: ignore
        
        for i in range(num_inputs[0]):
            attribute = cls.create_attribute(program_id, gl.GL_PROGRAM_INPUT, i) # type: ignore
            layout.append(attribute)
        
        layout.sort(key=lambda x: x.location)

        return layout

    @classmethod
    def introspect_uniforms(cls, program_id: int) -> list[Attribute]:
        uniforms: list[Attribute] = []

        num_uniforms = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_UNIFORM, gl.GL_ACTIVE_RESOURCES, num_uniforms) # type: ignore
        
        for i in range(num_uniforms[0]):
            attribute = cls.create_attribute(program_id, gl.GL_UNIFORM, i) # type: ignore
            if attribute.location == -1:
                continue
            uniforms.append(attribute)

        uniforms.sort(key=lambda x: x.location)

        return uniforms

    @classmethod
    def introspect_ubos(cls, program_id: int) -> list[DataBlock]:
        ubos: list[DataBlock] = []

        num_ubos = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_UNIFORM_BLOCK, gl.GL_ACTIVE_RESOURCES, num_ubos) # type: ignore
        
        for i in range(num_ubos[0]):
            block_name = cls.get_resource_name(program_id, gl.GL_UNIFORM_BLOCK, i) # type: ignore
            block_values = np.array([0, 0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, gl.GL_UNIFORM_BLOCK, i, 3,  # type: ignore
                                [gl.GL_BUFFER_BINDING, gl.GL_BUFFER_DATA_SIZE, gl.GL_NUM_ACTIVE_VARIABLES], 3, None, block_values) # type: ignore
            
            binding, data_size, num_vars = block_values
            
            members: list[Attribute] = []
            if num_vars > 0:
                var_indices = np.array([0] * num_vars, dtype=np.int32)
                gl.glGetProgramResourceiv(program_id, gl.GL_UNIFORM_BLOCK, i, 1, [gl.GL_ACTIVE_VARIABLES], num_vars, None, var_indices) # type: ignore
                
                for var_idx in var_indices:
                    attribute = cls.create_attribute(program_id, gl.GL_UNIFORM, var_idx) # type: ignore
                    members.append(attribute)
                    
            ubo = DataBlock(name=block_name, binding=binding, size=data_size, members=members)
            ubos.append(ubo)

        ubos.sort(key=lambda x: x.binding)

        return ubos

    @classmethod
    def introspect_ssbos(cls, program_id: int) -> list[DataBlock]:
        ssbos: list[DataBlock] = []
        num_ssbos = np.array([0], dtype=np.int32)
        gl.glGetProgramInterfaceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, gl.GL_ACTIVE_RESOURCES, num_ssbos) # type: ignore
        
        for i in range(num_ssbos[0]):
            block_name = cls.get_resource_name(program_id, gl.GL_SHADER_STORAGE_BLOCK, i) # type: ignore
            block_values = np.array([0, 0, 0], dtype=np.int32)
            gl.glGetProgramResourceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, i, 3,  # type: ignore
                                [gl.GL_BUFFER_BINDING, gl.GL_BUFFER_DATA_SIZE, gl.GL_NUM_ACTIVE_VARIABLES], 3, None, block_values) # type: ignore
            
            binding, data_size, num_vars = block_values
            
            members: list[Attribute] = []
            if num_vars > 0:
                var_indices = np.array([0] * num_vars, dtype=np.int32)
                gl.glGetProgramResourceiv(program_id, gl.GL_SHADER_STORAGE_BLOCK, i, 1, [gl.GL_ACTIVE_VARIABLES], num_vars, None, var_indices) # type: ignore
                
                for var_idx in var_indices:
                    attribute = cls.create_attribute(program_id, gl.GL_BUFFER_VARIABLE, var_idx) # type: ignore
                    members.append(attribute)

            ssbo = DataBlock(name=block_name, binding=binding, size=data_size, members=members)
            ssbos.append(ssbo)
            
        ssbos.sort(key=lambda x: x.binding)

        return ssbos

    @classmethod
    def introspect_program(cls, program_id: int) -> Introspection:
        layout = cls.introspect_layout(program_id)
        uniforms = cls.introspect_uniforms(program_id)
        ubos = cls.introspect_ubos(program_id)
        ssbos = cls.introspect_ssbos(program_id)
        targets = cls.introspect_targets(program_id)

        inputs = ResourceInputs(layout=layout, uniforms=uniforms, ubos=ubos, ssbos=ssbos)
        outputs = ResourceOutputs(targets=targets)
        introspection = Introspection(inputs, outputs)
        
        return introspection