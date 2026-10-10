#version 430 core

layout(location = 0) in vec2 sw_in_vert;
layout(location = 1) in vec2 sw_in_texcoord;

out vec2 TexCoords;

void main() {
    TexCoords = sw_in_texcoord;
    gl_Position = vec4(sw_in_vert, 0.0, 1.0);
}