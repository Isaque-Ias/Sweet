#version 460 core

// -----------------------------------------------------------------------------
// Mesh Attributes (Per-Vertex Inputs)
// -----------------------------------------------------------------------------
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texcoord_0;

// -----------------------------------------------------------------------------
// Uniform Buffer Object (UBO) - Shared Camera Data
// Bound to layout(binding = 0)
// -----------------------------------------------------------------------------

layout(std140, binding = 0) uniform CameraUBO {
    mat4 u_Projection;
    mat4 u_View;
};

// -----------------------------------------------------------------------------
// Shader Storage Buffer Object (SSBO) - Dynamic Array of Model Matrices
// Bound to layout(binding = 1)
// -----------------------------------------------------------------------------
struct InstanceData {
    mat4 model;
};

layout(std430, binding = 1) readonly buffer InstanceSSBO {
    InstanceData instances[];
};

// -----------------------------------------------------------------------------
// Outputs to Fragment Shader
// -----------------------------------------------------------------------------
out vec3 v_WorldPos;
out vec3 v_Normal;
out vec2 v_UV;

void main() {
    // Fetch the model matrix for current instance being rendered
    mat4 modelMatrix = instances[gl_InstanceID].model;

    // Transform vertex position to world space
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    v_WorldPos = worldPos.xyz;

    // Compute normal matrix to correctly transform normals (handles non-uniform scaling)
    mat3 normalMatrix = transpose(inverse(mat3(modelMatrix)));
    v_Normal = normalize(normalMatrix * normal);

    v_UV = texcoord_0;

    // Output final clip-space position
    gl_Position = u_Projection * u_View * worldPos;
}