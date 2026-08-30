#version 330 core

layout (triangles) in;
layout (triangle_strip, max_vertices = 18) out; // 3 vertices * 6 faces

uniform mat4 sw_ShadowMatrices[6]; // Array of 6 (Projection * LookAt) matrices

in vec3 g_Pos[];
out vec3 v_cube_uv;

void main() {
    for (int face = 0; face < 6; ++face) {
        gl_Layer = face; // Dynamically routes primitives to Cubemap Face 0..5

        for (int i = 0; i < 3; ++i) {
            v_cube_uv = g_Pos[i];
            
            vec4 clipPos = sw_ShadowMatrices[face] * vec4(g_Pos[i], 1.0);
            
            // Push depth to far plane z/w = 1.0
            gl_Position = clipPos.xyww; 
            
            EmitVertex();
        }
        EndPrimitive();
    }
}