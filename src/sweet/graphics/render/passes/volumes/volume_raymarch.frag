#version 460 core

in vec2 v_uv;
out vec4 Volume_Out;

uniform sampler2D u_SceneColor;
uniform sampler2D u_DepthTexture;
uniform sampler2D u_ShadowMap;
uniform sampler3D u_CloudNoise3D; // 3D Perlin-Worley Texture

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;
uniform vec3 sw_CameraPosition;
uniform vec3 sw_LightDirection;
uniform vec3 sw_LightColor;
uniform float sw_Time;

uniform mat4 sw_LightView;
uniform mat4 sw_LightProjection;

#define VOLUME_TYPE_GLOBAL_HEIGHT 0u
#define VOLUME_TYPE_BOX           1u
#define VOLUME_TYPE_SPHERE        2u

struct VolumeObject {
    mat4 inv_transform;   // Transforms World Space -> Local Space [-1, 1]
    vec4 color;           // RGB: Scattering Color, A: Base Density
    vec4 parameters;      // x: Phase g, y: Height Falloff, z: Ground Level, w: Absorption
    vec4 cloud_params;    // x: Detail Scale, y: Animate Speed, z: Soft Edge, w: Height Shape Mode
    uint type;
    uint pad0;
    uint pad1;
    uint pad2;
};

layout(std430, binding = 7) readonly buffer sw_Volumes {
    uint u_VolumeCount;
    uint _pad0;
    uint _pad1;
    uint _pad2;
    VolumeObject volumes[];
};

// --- Cloud Height Gradient Profile ---
// Shapes volume vertically: zero at bottom, dense in middle, tapering at top
float GetCloudHeightSignal(float normalizedY) {
    // normalizedY goes from 0.0 (bottom of box) to 1.0 (top of box)
    return smoothstep(0.0, 0.2, normalizedY) * (1.0 - smoothstep(0.7, 1.0, normalizedY));
}

// Evaluate Density using 3D Texture
float SampleVolumeDensity(VolumeObject vol, vec3 worldPos) {
    if (vol.type != VOLUME_TYPE_BOX) return 0.0;

    // Transform world position to local bounding space [-1.0, 1.0]
    vec3 localPos = (vol.inv_transform * vec4(worldPos, 1.0)).xyz;

    // Out-of-bounds check
    if (any(greaterThanEqual(abs(localPos), vec3(1.0)))) {
        return 0.0;
    }

    // Local normalized coordinates [0, 1]
    vec3 boxUV = localPos * 0.5 + 0.5;

    // 1. Soft Box Edge Falloff
    vec3 edgeDist = min(boxUV, 1.0 - boxUV);
    float edgeFactor = smoothstep(0.0, vol.cloud_params.z, min(edgeDist.x, min(edgeDist.y, edgeDist.z)));

    // 2. Vertical Cloud Profile
    float heightSignal = GetCloudHeightSignal(boxUV.y);

    // 3. Sample 3D Noise
    float detailScale = max(vol.cloud_params.x, 0.001); // Guard against divide/multiply by 0
    float animSpeed = vol.cloud_params.y;

    // Option A: World-Space Tiling (for large, seamless cloudscapes)
    vec3 uvw = worldPos * detailScale + vec3(sw_Time * animSpeed * 0.05, sw_Time * animSpeed * 0.01, 0.0);
    
    // Option B: Box-Local Tiling (stretches with the box size)
    // vec3 uvw = boxUV * detailScale + vec3(sw_Time * animSpeed * 0.05, 0.0, 0.0);

    vec4 noiseSample = texture(u_CloudNoise3D, uvw);
    
    float baseNoise = noiseSample.r * 0.6 + noiseSample.g * 0.4;
    float highFreqErosion = noiseSample.b * 0.3 + noiseSample.a * 0.2;
    
    float finalCloudShape = smoothstep(1.0 - baseNoise, 1.0, heightSignal - highFreqErosion);

    return vol.color.a * finalCloudShape * edgeFactor;
}

// --- Henyey-Greenstein & Shadowing ---
float HenyeyGreenstein(float cosTheta, float g) {
    float g2 = g * g;
    return (1.0 - g2) / (4.0 * 3.14159265 * pow(1.0 + g2 - 2.0 * g * cosTheta, 1.5));
}

float SampleShadow(vec3 worldPos) {
    mat4 lightSpaceMatrix = sw_LightProjection * sw_LightView;
    vec4 lightSpacePos = lightSpaceMatrix * vec4(worldPos, 1.0);
    vec3 projCoords = lightSpacePos.xyz / lightSpacePos.w;
    projCoords = projCoords * 0.5 + 0.5;

    if (projCoords.z > 1.0 || projCoords.z < 0.0) return 1.0;

    float closestDepth = texture(u_ShadowMap, projCoords.xy).r;
    return (projCoords.z - 0.005 > closestDepth) ? 0.0 : 1.0;
}

vec3 ReconstructWorldPos(vec2 uv, float depth) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 viewPos = sw_InvProjection * ndc;
    viewPos /= viewPos.w;
    return (sw_InvView * viewPos).xyz;
}

void main() {
    vec3 sceneColor = texture(u_SceneColor, v_uv).rgb;
    float depth = texture(u_DepthTexture, v_uv).r;

    vec3 rayStart = sw_CameraPosition;
    vec3 rayEnd = ReconstructWorldPos(v_uv, depth);
    vec3 rayVec = rayEnd - rayStart;
    float rayLength = length(rayVec);
    vec3 rayDir = rayVec / rayLength;

    const int NUM_STEPS = 48;
    float stepSize = rayLength / float(NUM_STEPS);

    // Screen-Space Interleaved Dithering to hide step artifacts
    float dither = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
    float currentT = stepSize * dither;

    float transmittance = 1.0;
    vec3 accumulatedInscattering = vec3(0.0);
    float cosTheta = dot(rayDir, sw_LightDirection);

    for (int i = 0; i < NUM_STEPS; ++i) {
        if (currentT >= rayLength || transmittance < 0.01) break;

        vec3 currentPos = rayStart + rayDir * currentT;

        for (uint v = 0u; v < u_VolumeCount; ++v) {
            VolumeObject vol = volumes[v];
            float density = SampleVolumeDensity(vol, currentPos);

            if (density > 0.001) {
                float totalExtinction = density + vol.parameters.w;
                float stepTransmittance = exp(-totalExtinction * stepSize);

                float shadow = SampleShadow(currentPos);
                float phase = HenyeyGreenstein(cosTheta, vol.parameters.x);

                vec3 lightScattering = sw_LightColor * shadow * phase * vol.color.rgb;
                vec3 stepInscattering = lightScattering * (density / max(totalExtinction, 0.0001)) * (1.0 - stepTransmittance);

                accumulatedInscattering += transmittance * stepInscattering;
                transmittance *= stepTransmittance;
            }
        }

        currentT += stepSize;
    }

    vec3 finalColor = sceneColor * transmittance + accumulatedInscattering;
    Volume_Out = vec4(finalColor, 1.0);
}