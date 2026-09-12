#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 out_color;

uniform sampler2D Present_Light;

void main()
{
    vec3 color = texture(Present_Light, v_uv).rgb;

    out_color = vec4(color, 1.0);
}