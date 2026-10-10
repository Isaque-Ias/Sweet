#version 430 core

layout(location = 0) in vec3 sw_position;
layout(location = 1) in vec2 sw_texcoord;
layout(location = 2) in vec3 sw_normal;

struct InstanceData {
    mat4 sw_model;
    vec4 sw_UV;
    vec4 sw_color;
};

layout(std430, binding = 1) readonly buffer sw_InstanceBuffer {
    InstanceData instances[];
};

layout(std140, binding = 0) uniform sw_Camera {
    mat4 sw_projection;
    mat4 sw_view;
    vec3 uCamPos;
} camera;

out vec2 v_texcoord;
out vec4 v_color;
out vec3 v_normal;
out vec3 v_frag_pos;
out vec3 v_cam_pos;

void main()
{
    InstanceData instance = instances[gl_InstanceID];

    vec4 world_position = instance.sw_model * vec4(sw_position, 1.0);
    v_frag_pos = vec3(world_position); 
    
    gl_Position = camera.sw_projection * camera.sw_view * world_position;

    v_normal = mat3(transpose(inverse(instance.sw_model))) * sw_normal;

    vec2 flipped_a_texcoord = vec2(sw_texcoord.x, 1.0 - sw_texcoord.y);
    v_texcoord = flipped_a_texcoord * instance.sw_UV.zw + instance.sw_UV.xy;
    v_color = instance.sw_color;
    v_cam_pos = camera.uCamPos;
}