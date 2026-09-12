#version 330 core
out vec4 LumPass;
in vec2 v_uv;

uniform sampler2D hdrSceneTexture;

const vec3 LUMINANCE_VECTOR = vec3(0.2126, 0.7152, 0.0722);

void main() {
    vec3 color = texture(hdrSceneTexture, v_uv).rgb;

    // 1. Sanitize input to catch NaNs or negative lighting values from earlier passes
    color = max(color, vec3(0.0)); 

    float luminance = dot(color, LUMINANCE_VECTOR);

    // 2. Safe log calculation (NEVER allow log2 to touch 0.0)
    float logLuminance = log2(max(luminance, 0.0001));

    LumPass = vec4(logLuminance, 0.0, 0.0, 1.0);
}