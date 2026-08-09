#version 430 core

void main() {
    // Generates 3 vertices covering [-1, 1] NDC space:
    // gl_VertexID = 0 -> (-1.0, -1.0)
    // gl_VertexID = 1 -> ( 3.0, -1.0)
    // gl_VertexID = 2 -> (-1.0,  3.0)
    float x = -1.0 + float((gl_VertexID & 1) << 2);
    float y = -1.0 + float((gl_VertexID & 2) << 1);
    
    gl_Position = vec4(x, y, 0.0, 1.0);
}