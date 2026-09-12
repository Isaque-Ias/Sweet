#version 330

// Half-extent of the cube
const float e = 1.0; 

// 8 unique corners of the cube
const vec3 pos[8] = vec3[8](
    vec3(-e, -e, -e), // 0: Back-Bottom-Left
    vec3( e, -e, -e), // 1: Back-Bottom-Right
    vec3( e,  e, -e), // 2: Back-Top-Right
    vec3(-e,  e, -e), // 3: Back-Top-Left
    vec3(-e, -e,  e), // 4: Front-Bottom-Left
    vec3( e, -e,  e), // 5: Front-Bottom-Right
    vec3( e,  e,  e), // 6: Front-Top-Right
    vec3(-e,  e,  e)  // 7: Front-Top-Left
);

// 36 indices mapping to the 12 triangles (6 quad faces)
const int indices[36] = int[36](
    0, 1, 2,  0, 2, 3,  // Back (-Z)
    4, 6, 5,  4, 7, 6,  // Front (+Z)
    0, 5, 1,  0, 4, 5,  // Bottom (-Y)
    2, 6, 7,  2, 7, 3,  // Top (+Y)
    0, 3, 7,  0, 7, 4,  // Left (-X)
    1, 6, 2,  1, 5, 6   // Right (+X)
);

void main() {
    // Lookup the vertex index using the built-in system variable gl_VertexID
    int index = indices[gl_VertexID];
    
    gl_Position = vec4(pos[index], 1.0);
}