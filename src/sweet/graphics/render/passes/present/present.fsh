#version 430 core

layout(location = 0) out vec4 FragColor;

in vec2 v_uv;

uniform sampler2D u_lighting;

void main()
{
    FragColor = texture(u_lighting, v_uv);
}