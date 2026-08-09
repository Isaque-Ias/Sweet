#version 430 core

layout(location = 0) out vec4 g_albedo;
layout(location = 1) out vec4 g_normal;

void main() {
    g_albedo = vec4(1.0, 1.0, 1.0, 1.0); // Solid White
    g_normal = vec4(1.0, 1.0, 1.0, 1.0); // Solid White
}