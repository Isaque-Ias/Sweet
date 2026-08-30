#version 330 core

in vec2 v_uv;
out vec4 FragColor;

uniform sampler2D u_lighting_texture;
uniform sampler2D u_depth_texture;
uniform samplerCube u_skybox_cubemap;

uniform mat4 u_inv_proj;
uniform mat4 u_inv_view;

void main() {
    vec4 scene_color = texture(u_lighting_texture, v_uv);
    float depth = texture(u_depth_texture, v_uv).r;

    if (depth >= 0.99999) {
        vec4 ndc = vec4(v_uv * 2.0 - 1.0, 1.0, 1.0);
        vec4 view_space_dir = u_inv_proj * ndc;
        view_space_dir = vec4(view_space_dir.xy, -1.0, 0.0);
        
        vec3 world_dir = normalize((u_inv_view * view_space_dir).xyz);
        
        vec4 skybox_color = texture(u_skybox_cubemap, world_dir);
        FragColor = skybox_color;
    } else {
        // Keep the rendered lit scene object
        FragColor = scene_color;
    }
}