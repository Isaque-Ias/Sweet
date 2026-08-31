#version 330 core

out vec4 BloomBlur_Out;
in vec2 v_uv;

uniform sampler2D Bloom_Input;

void main() {
    vec3 sum = vec3(0.0);
    float totalWeight = 0.0;
    
    // A 5x5 neighborhood search (25 samples total)
    int radius = 3;
    float spread = 4.0; // Increase this to make the blur wider

    // Approximate screen resolution scaling (or pass resolution as a uniform)
    vec2 texelSize = 1.0 / vec2(textureSize(Bloom_Input, 0));

    for (int x = -radius; x <= radius; x++) {
        for (int y = -radius; y <= radius; y++) {
            vec2 offset = vec2(float(x), float(y)) * texelSize * spread;
            
            // Simple distance-based weight
            float weight = 1.0 / (float(abs(x) + abs(y)) + 1.0);
            
            sum += texture(Bloom_Input, v_uv + offset).rgb * weight;
            totalWeight += weight;
        }
    }

    BloomBlur_Out = vec4(sum / totalWeight, 1.0);
}