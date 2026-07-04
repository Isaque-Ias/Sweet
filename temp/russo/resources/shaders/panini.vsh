#version 430 core

layout(location = 0) in vec2 sw_in_vert;       // Posição do quadrado da tela (-1 a 1)
layout(location = 1) in vec2 sw_in_texcoord;   // Coordenadas UV (0 a 1)

out vec2 TexCoords;

void main() {
    TexCoords = sw_in_texcoord;
    // Desenha o quadrado plano cobrindo a tela toda
    gl_Position = vec4(sw_in_vert, 0.0, 1.0);
}
