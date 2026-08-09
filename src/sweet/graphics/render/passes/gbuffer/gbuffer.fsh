#version 430 core

layout(location = 0) out vec4 GBuffer_Normals;
layout(location = 1) out vec4 GBuffer_Depth;
layout(location = 2) out vec4 GBuffer_Albedo;

in vec3 v_world_position;
in vec3 v_world_normal;
in vec2 v_texcoord;
in vec4 v_view_position;

uniform float sw_Near = 0.1;   // Camera Near Plane
uniform float sw_Far = 100.0;  // Camera Far Plane
uniform vec4 u_base_color;

void main()
{
    vec3 normal = normalize(v_world_normal);

    vec4 base_color = (u_base_color == vec4(0.0)) ? vec4(0.8, 0.8, 0.8, 1.0) : u_base_color;
    GBuffer_Albedo = base_color;
    GBuffer_Normals = vec4(normal * 0.5 + 0.5, 1.0);

    // Calculate Linear Depth [0.0, 1.0]
    float linear_depth = (-v_view_position.z - sw_Near) / (sw_Far - sw_Near);
    linear_depth = clamp(linear_depth, 0.0, 1.0);

    GBuffer_Depth = vec4(vec3(linear_depth), 1.0);
}