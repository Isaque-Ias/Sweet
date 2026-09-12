#version 330 core
out vec4 TonePass;
in vec2 v_uv;

uniform sampler2D TonehdrSceneTexture;   // High-intensity HDR image
uniform sampler2D avgLuminanceTex;   // 1x1 downsampled log-luminance texture

// Key exposure control parameters
uniform float middleGray = 0.18;      // Target middle-gray brightness (18% gray standard)
uniform float minExposure = 0.00001;  // Protects against total pitch blackness
uniform float maxExposure = 10.0;     // Prevents extreme brightening in dark rooms

// Narkowicz ACES Filmic Fit
vec3 ACESFilmic(vec3 x) {
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
    // 1. Fetch raw HDR color
    vec3 hdrColor = texture(TonehdrSceneTexture, v_uv).rgb;
    
    // 2. Retrieve dynamic geometric average scene luminance
    float logAvgLuminance = texture(avgLuminanceTex, vec2(0.5, 0.5)).r;
    float avgLuminance = exp2(logAvgLuminance);
    
    // 3. Compute auto-exposure factor dynamically based on current scene average
    float exposure = middleGray / max(avgLuminance, 0.0001);
    exposure = clamp(exposure, minExposure, maxExposure);
    
    // 4. Apply dynamic exposure adjustment
    vec3 exposedColor = hdrColor * exposure;
    
    // 5. Tonemap highlights gracefully down to [0.0, 1.0] range
    //vec3 ldrColor = ACESFilmic(exposedColor);
    vec3 ldrColor = exposedColor / (exposedColor + vec3(1.0));
    
    // 6. Gamma Correction for display (Linear -> sRGB)
    //ldrColor = pow(ldrColor, vec3(1.0 / 2.2));
    
    TonePass = vec4(ldrColor, 1.0);
}