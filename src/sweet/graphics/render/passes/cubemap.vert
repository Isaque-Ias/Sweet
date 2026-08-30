#version 330 core

const vec3 CUBE_POSITIONS[36] = vec3[36](
    // Front face
    vec3(-1,  1, -1), vec3(-1, -1, -1), vec3( 1, -1, -1),
    vec3( 1, -1, -1), vec3( 1,  1, -1), vec3(-1,  1, -1),
    // Back face
    vec3(-1, -1,  1), vec3(-1,  1,  1), vec3( 1,  1,  1),
    vec3( 1,  1,  1), vec3( 1, -1,  1), vec3(-1, -1,  1),
    // Left face
    vec3(-1,  1,  1), vec3(-1,  1, -1), vec3(-1, -1, -1),
    vec3(-1, -1, -1), vec3(-1, -1,  1), vec3(-1,  1,  1),
    // Right face
    vec3( 1,  1, -1), vec3( 1,  1,  1), vec3( 1, -1,  1),
    vec3( 1, -1,  1), vec3( 1, -1, -1), vec3( 1,  1, -1),
    // Top face
    vec3(-1,  1,  1), vec3( 1,  1,  1), vec3( 1,  1, -1),
    vec3( 1,  1, -1), vec3(-1,  1, -1), vec3(-1,  1,  1),
    // Bottom face
    vec3(-1, -1, -1), vec3( 1, -1, -1), vec3( 1, -1,  1),
    vec3( 1, -1,  1), vec3(-1, -1,  1), vec3(-1, -1, -1)
);

out vec3 g_Pos;

void main() {
    g_Pos = CUBE_POSITIONS[gl_VertexID];
    gl_Position = vec4(g_Pos, 1.0);
}