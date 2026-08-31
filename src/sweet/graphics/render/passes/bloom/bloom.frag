#version 330 core

out vec4 Bloom_Out;
in vec2 v_uv;

uniform sampler2D Bloom_Light;

void main() {
    vec3 color = texture(Bloom_Light, v_uv).rgb;
    
    // Simple brightness/luminance threshold
    float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
    
    if (brightness >= 1.0) {
        Bloom_Out = vec4(color, 1.0);
    } else {
        Bloom_Out = vec4(0.0, 0.0, 0.0, 1.0);
    }
}