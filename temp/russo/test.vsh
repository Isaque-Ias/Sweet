#version 330 core

// 1. Data coming from the Mesh VAO
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec3 in_color;

// 2. Camera Matrices coming from the UBO (binding = 0)
layout (std140) uniform CameraMatrices {
    mat4 projection;
    mat4 view;
};

// Uniform for object placement in the world
uniform mat4 model;

// Output to pass to the Fragment Shader
out vec3 vertexColor;

void main() {
    // Standard 3D transformation pipeline: Projection * View * Model * Position
    gl_Position = projection * view * model * vec4(in_position, 1.0);
    
    // Pass the vertex color directly through
    vertexColor = in_color;
}
