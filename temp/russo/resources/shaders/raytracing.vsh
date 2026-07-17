#version 300 es
layout(location = 0) in vec2 sw_position;

out vec2 v_uv;

void main() {
    v_uv = sw_position;
    gl_Position = vec4(sw_position, 0.0, 1.0);
}