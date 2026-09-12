#version 460 core

out vec4 outFog;

in vec2 v_uv;

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;
uniform vec3 sw_CameraPosition;
uniform vec3 sw_LightDirection;
uniform vec3 sw_LightColor;

uniform sampler2D fogSceneColor;
uniform sampler2D fogDepth;
uniform sampler2D fogShadow;
uniform mat4 u_LightProjection;
uniform mat4 u_LightView;

struct FogVolume {
    mat4 invWorldMatrix;
    vec3 boundsMin;
    float densityScale;
    vec3 boundsMax;
    float absorption;
    vec4 scatteringColor;
    // Note: Bindless handles in GLSL std430 buffers use uvec2 (64-bit uint) for portability
    uvec2 noiseHandle; 
};

layout(std430, binding = 6) readonly buffer sw_Volumes {
    uint u_FogVolumeCount;
    FogVolume u_Volumes[];
};

// Ray-AABB intersection test
bool intersectAABB(vec3 rayOrigin, vec3 rayDir, vec3 boxMin, vec3 boxMax, out float t0, out float t1) {
    vec3 invR = 1.0 / rayDir;
    vec3 tbot = invR * (boxMin - rayOrigin);
    vec3 ttop = invR * (boxMax - rayOrigin);
    vec3 tmin = min(ttop, tbot);
    vec3 tmax = max(ttop, tbot);
    vec2 t = max(tmin.xx, tmin.yz);
    t0 = max(t.x, t.y);
    t = min(tmax.xx, tmax.yz);
    t1 = min(t.x, t.y);
    return t0 <= t1 && t1 > 0.0;
}

float sampleShadow(vec3 worldPos) {
    mat4 u_LightSpaceMatrix = u_LightProjection * u_LightView;

    vec4 lightSpacePos = u_LightSpaceMatrix * vec4(worldPos, 1.0);
    vec3 projCoords = lightSpacePos.xyz / lightSpacePos.w;
    projCoords = projCoords * 0.5 + 0.5;
    
    if (projCoords.z > 1.0) return 1.0;
    
    // Manual depth test
    float closestDepth = texture(fogShadow, projCoords.xy).r;
    float currentDepth = projCoords.z - 0.002;
    
    return currentDepth > closestDepth ? 0.0 : 1.0;
}

// Density evaluation across active fog volumes
float sampleDensity(vec3 worldPos, out vec3 outScattering) {
    float totalDensity = 0.0;
    outScattering = vec3(0.0);

    for (uint i = 0u; i < u_FogVolumeCount; ++i) {
        FogVolume vol = u_Volumes[i];
        vec3 localPos = (vol.invWorldMatrix * vec4(worldPos, 1.0)).xyz;

        // Check unit bounds [-0.5, 0.5]
        if (all(greaterThanEqual(localPos, vec3(-0.5))) && all(lessThanEqual(localPos, vec3(0.5)))) {
            vec3 uvw = localPos + 0.5; // Map to [0, 1] 3D UVs
            
            // Simple procedural noise fallback if bindless is not enabled/configured
            // Replace this with your noise sampling logic
            float noise = 1.0;

            float density = noise * vol.densityScale;
            totalDensity += density;
            outScattering += vol.scatteringColor.rgb * density;
        }
    }
    return totalDensity;
}

void main() {
    vec2 uv = v_uv;
    float depth = texture(fogDepth, uv).r;

    // Reconstrução de NDC para View Space
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 viewPos = sw_InvProjection * ndc;
    viewPos /= viewPos.w;
    
    // Converte para World Space
    vec3 worldTarget = (sw_InvView * viewPos).xyz;
    vec3 rayOrigin = sw_CameraPosition;
    vec3 rayDir = normalize(worldTarget - rayOrigin);
    
    // Se a profundidade for 1.0 (sem mesh / skybox), define uma distância máxima limite
    float maxDist = length(worldTarget - rayOrigin);
    if (depth >= 0.9999) {
        maxDist = 100.0; // Distância limite de renderização da névoa no fundo
    }

    // Parâmetros de Raymarching
    int steps = 64;
    float stepSize = maxDist / float(steps);
    float transmittance = 1.0;
    vec3 accumulatedLight = vec3(0.0);

    for (int i = 0; i < steps; ++i) {
        float t = (float(i) + 0.5) * stepSize;
        if (t >= maxDist) break;

        vec3 p = rayOrigin + rayDir * t;
        vec3 scatteringColor;
        float density = sampleDensity(p, scatteringColor);

        if (density > 0.001) {
            float shadow = sampleShadow(p);
            vec3 lightInjected = sw_LightColor * shadow;

            float extinction = density;
            float stepTransmittance = exp(-extinction * stepSize);

            accumulatedLight += transmittance * (scatteringColor * lightInjected) * (1.0 - stepTransmittance);
            transmittance *= stepTransmittance;

            if (transmittance < 0.01) break;
        }
    }

    vec3 sceneColor = texture(fogSceneColor, uv).rgb;
    
    // Exibe a névoa acumulada até onde há geometria ou até o limite no fundo
    outFog = vec4(sceneColor * transmittance + accumulatedLight, 1.0);
}