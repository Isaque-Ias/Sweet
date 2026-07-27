#version 330 core

// Input from the Vertex Shader (must match name and type)
in vec3 vertexColor;

// Final pixel output color
out vec4 fragColor;

void main() {
    // Output the mesh color with 100% opacity (Alpha = 1.0)
    fragColor = vec4(vertexColor, 1.0);
}
