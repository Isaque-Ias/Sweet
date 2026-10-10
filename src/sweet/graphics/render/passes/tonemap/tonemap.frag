#version 330 core
out vec4 TonePass;
in vec2 v_uv;

uniform sampler2D TonehdrSceneTexture;   // Base HDR Scene
//uniform sampler2D HDRBloomTone;          // Upsampled Bloom Pyramid (Final output)
uniform sampler2D avgLuminanceTex;       // Log-Luminance Texture

uniform float avgLuminanceTexLod = 0.0;
uniform float middleGray = 0.4;
uniform float minExposure = 0.00001;
uniform float maxExposure = 2.0;

// Bloom controls
uniform float u_bloomIntensity = 0.04;    // Standard range: 0.02 - 0.08
uniform vec3  u_bloomTint = vec3(1.0);    // Allows color tinting blooming highlights

// Krzysztof Narkowicz ACES Filmic Curve (Industry standard curve)
vec3 ACESFilmic(vec3 x) {
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
    // 1. Fetch raw HDR color and Bloom energy
    vec3 hdrColor = texture(TonehdrSceneTexture, v_uv).rgb;
    vec3 bloomColor = vec3(0.0);//texture(HDRBloomTone, v_uv).rgb;

    // 2. Retrieve dynamic geometric average scene luminance
    float logAvgLuminance = textureLod(avgLuminanceTex, vec2(0.5, 0.5), avgLuminanceTexLod).r;
    float avgLuminance = exp2(logAvgLuminance);

    // 3. Compute exposure factor
    float exposure = middleGray / max(avgLuminance, 0.0001);
    exposure = clamp(exposure, minExposure, maxExposure);

    // 4. Apply exposure scaling to both scene and bloom light
    vec3 exposedColor = hdrColor * exposure;
    vec3 exposedBloom = bloomColor * exposure * u_bloomTint * u_bloomIntensity;

    // 5. Combine Scene Light + Bloom Glow in HDR linear space
    vec3 compositeHDR = exposedColor + exposedBloom;

    // 6. Map HDR radiance curve to displayable [0.0, 1.0] range
    vec3 ldrColor = ACESFilmic(compositeHDR);

    // 7. Gamma Correction for sRGB displays
    ldrColor = pow(ldrColor, vec3(1.0 / 2.2));

    TonePass = vec4(ldrColor, 1.0);
}