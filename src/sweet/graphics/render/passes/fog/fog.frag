#version 450 core

in vec2 v_uv;
out vec4 FogColor;

uniform sampler2D u_SceneColor;
uniform sampler2D u_DepthTexture;

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

// Fog parameters
uniform vec3 sw_FogColor = vec3(0.6, 0.7, 0.8);
uniform float sw_FogDensity = 0.0005; // Adjusted for large-scale terrain
uniform float sw_FogHeightDensity = 0.005; // Vertical falloff rate
uniform float sw_FogBaseHeight = 0.0;     // Base height level of ground fog

vec3 GetWorldPosition(vec2 texCoords, float depth) {
    vec4 ndc = vec4(texCoords * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 viewSpace = sw_InvProjection * ndc;
    viewSpace /= viewSpace.w;
    vec4 worldSpace = sw_InvView * viewSpace;
    return worldSpace.xyz;
}

void main() {
    vec3 sceneColor = texture(u_SceneColor, v_uv).rgb;
    float depth = texture(u_DepthTexture, v_uv).r;

    // Skip skybox pixels (depth near far plane / 1.0)
    if (depth >= 0.99999) {
        FogColor = vec4(sceneColor, 1.0);
        return;
    }

    vec3 worldPos = GetWorldPosition(v_uv, depth);
    vec3 cameraPos = sw_InvView[3].xyz;

    float dist = length(worldPos - cameraPos);

    float heightFactor = exp(-sw_FogHeightDensity * (worldPos.y - sw_FogBaseHeight));
    float fogFactor = 1.0 - exp(-dist * sw_FogDensity * heightFactor);
    fogFactor = clamp(fogFactor, 0.0, 1.0);

    vec3 finalColor = mix(sceneColor, sw_FogColor, fogFactor);
    FogColor = vec4(finalColor, 1.0);
}