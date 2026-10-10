#version 330 core
out vec4 Bloom_Out;
in vec2 v_uv;

uniform sampler2D Bloom_Light;
uniform float u_threshold = 1.0; // Threshold cutoff (e.g., 1.0)
uniform float u_knee = 0.5;      // Soft knee curve width (e.g., 0.5)

float Luma(vec3 color) {
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void main() {
    vec3 color = texture(Bloom_Light, v_uv).rgb;
    
    // Calculate brightness curve with soft knee
    float brightness = max(color.r, max(color.g, color.b));
    float soft = brightness - u_threshold + u_knee;
    soft = clamp(soft, 0.0, 2.0 * u_knee);
    soft = (soft * soft) / (4.0 * u_knee + 0.00001);
    
    float weight = max(soft, brightness - u_threshold) / max(brightness, 0.00001);
    vec3 extracted = color * weight;

    // Apply Karis Weighting on the extract pass to prevent bright single-pixel fireflies
    float luma = Luma(extracted);
    extracted *= 1.0 / (1.0 + luma);

    Bloom_Out = vec4(max(extracted, vec3(0.0)), 1.0);
}