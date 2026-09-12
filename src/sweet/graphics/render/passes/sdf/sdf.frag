#version 460 core
#extension GL_ARB_bindless_texture : enable
#extension GL_NV_gpu_shader5 : enable

// G-Buffer Output Attachments
layout(location = 0) out vec4 gAlbedo;
layout(location = 1) out vec4 gNormals;

// Uniforms
layout(location = 0) uniform mat4 u_InvProj;
layout(location = 1) uniform mat4 u_InvView;
layout(location = 2) uniform mat4 u_Proj;
layout(location = 3) uniform vec3 u_CameraPos;

// -----------------------------------------------------------------------------
// Bindless Data Structures
// -----------------------------------------------------------------------------
struct SDFVolume {
    mat4 invWorldMatrix; // Transform world ray into local SDF space
    vec3 boundsMin;      // AABB min for early ray exit
    uint type;           // 0 = Sphere, 1 = Box, 2 = Torus, 3 = Noise Blend
    vec3 boundsMax;      // AABB max
    float radius;        // Generic parameter (e.g. sphere radius, torus radius)
    vec4 albedo;
    vec3 params;         // Additional SDF dimensions / parameters
    float padding;
};

layout(std430, binding = 0) readonly buffer SDFVolumeBuffer {
    uint u_SDFCount;
    SDFVolume u_SDFs[];
};

// -----------------------------------------------------------------------------
// SDF Primitives (Evaluated in Local Space)
// -----------------------------------------------------------------------------
float sdSphere(vec3 p, float r) {
    return length(p) - r;
}

float sdBox(vec3 p, vec3 b) {
    vec3 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

float mapPrimitive(vec3 localPos, SDFVolume vol) {
    if (vol.type == 0u) return sdSphere(localPos, vol.radius);
    if (vol.type == 1u) return sdBox(localPos, vol.params);
    return sdSphere(localPos, vol.radius);
}

// Global scene distance field evaluating all volumes bindlessly
float mapScene(vec3 worldPos, out vec4 outAlbedo) {
    float minDist = 1e6;
    outAlbedo = vec4(0.0);

    for (uint i = 0u; i < u_SDFCount; ++i) {
        SDFVolume vol = u_SDFs[i];
        vec3 localPos = (vol.invWorldMatrix * vec4(worldPos, 1.0)).xyz;
        
        float dist = mapPrimitive(localPos, vol);
        if (dist < minDist) {
            minDist = dist;
            outAlbedo = vol.albedo;
        }
    }
    return minDist;
}

// Analytical Normal calculation using finite differences
vec3 calculateNormal(vec3 p) {
    vec4 dummy;
    float h = 0.001;
    vec2 k = vec2(1.0, -1.0);
    return normalize(
        k.xyy * mapScene(p + k.xyy * h, dummy) +
        k.yyx * mapScene(p + k.yyx * h, dummy) +
        k.yxy * mapScene(p + k.yxy * h, dummy) +
        k.xxx * mapScene(p + k.xxx * h, dummy)
    );
}

void main() {
    // Reconstruct world space ray direction from NDC
    vec2 ndc = (gl_FragCoord.xy / vec2(textureSize(u_InvProj, 0))) * 2.0 - 1.0; // Assume screen dimension pass
    vec4 target = u_InvProj * vec4(ndc, 1.0, 1.0);
    vec3 rayDir = normalize((u_InvView * vec4(normalize(target.xyz / target.w), 0.0)).xyz);
    vec3 rayOrigin = u_CameraPos;

    // Sphere Tracing loop
    float t = 0.0;
    float maxDist = 200.0;
    bool hit = false;
    vec4 hitAlbedo = vec4(0.0);

    for (int i = 0; i < 128; ++i) {
        vec3 p = rayOrigin + rayDir * t;
        float d = mapScene(p, hitAlbedo);
        if (d < 0.001) {
            hit = true;
            break;
        }
        t += d;
        if (t >= maxDist) break;
    }

    if (!hit) discard;

    vec3 hitPos = rayOrigin + rayDir * t;
    vec3 N = calculateNormal(hitPos);

    // Compute hardware Depth Buffer value to write to gl_FragDepth
    vec4 clipPos = u_Proj * (u_InvView * vec4(hitPos, 1.0));
    float ndcDepth = clipPos.z / clipPos.w;
    gl_FragDepth = ndcDepth * 0.5 + 0.5; // Map from [-1, 1] to [0, 1]

    gAlbedo = hitAlbedo;
    gNormals = vec4(N * 0.5 + 0.5, 1.0); // Encoded [0, 1] normals
}