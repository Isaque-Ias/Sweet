#version 330
layout(triangles) in;
layout(triangle_strip, max_vertices = 18) out;

uniform mat4 sw_CubemapMVP[6];
out vec3 v_pos;

void main() {
    for (int face = 0; face < 6; ++face) {
        gl_Layer = face;
        for (int i = 0; i < 3; ++i) {
            vec4 pos = gl_in[i].gl_Position;
            v_pos = pos.xyz;
            gl_Position = sw_CubemapMVP[face] * pos;
            EmitVertex();
        }
        EndPrimitive();
    }
}