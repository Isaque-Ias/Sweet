#version 430 core

out vec4 FragColor;
in vec2 TexCoords;

layout(binding = 0) uniform sampler2D screenTexture;
layout(binding = 1) uniform sampler2D depthTexture; // <-- Must match exactly

uniform float nearPlane = 0.1f;
uniform float farPlane = 100.0f;
uniform float blurStart = 10.0f;
uniform float blurEnd = 50.0f;

float LinearizeDepth(float depth) {
    float z = depth * 2.0 - 1.0; 
    return (2.0 * nearPlane * farPlane) / (farPlane + nearPlane - z * (farPlane - nearPlane));	
}

void main() {
    float depthVal = texture(depthTexture, TexCoords).r; // <-- Triggers compiler retention
    float depth = LinearizeDepth(depthVal);

    float blurFactor = clamp((depth - blurStart) / (blurEnd - blurStart), 0.0, 1.0);
    vec4 sharpColor = texture(screenTexture, TexCoords);

    if (blurFactor <= 0.0) {
        FragColor = sharpColor;
        return;
    }

    vec2 texelSize = 1.0 / textureSize(screenTexture, 0);
    vec4 blurredColor = vec4(0.0);
    
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            vec2 offset = vec2(float(x), float(y)) * texelSize;
            blurredColor += texture(screenTexture, TexCoords + offset);
        }
    }
    blurredColor /= 9.0;

    FragColor = mix(sharpColor, blurredColor, blurFactor);
}