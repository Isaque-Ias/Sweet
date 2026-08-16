#version 460 core

in vec2 v_uv;

layout(location = 0) out float SSAO_Out;

uniform sampler2D SSAO_Depth;
uniform sampler2D SSAO_Normals;
uniform sampler2D SSAO_Noise; // 4x4 repeating noise texture

uniform mat4 sw_Projection;
uniform mat4 sw_InvProjection;

uniform vec2 sw_Resolution;
uniform float sw_Radius;
uniform float sw_Bias;

uniform float sw_Intensity = 2.0;
uniform float sw_Power = 3.0;

const int SAMPLE_COUNT = 16;

// Hemisphere samples (Z in [0, 1], clustered toward origin)
const vec3 samples[SAMPLE_COUNT] = vec3[](
    vec3( 0.0400,  0.0300, 0.1000),
    vec3(-0.1200,  0.0800, 0.1500),
    vec3( 0.1800, -0.1100, 0.2200),
    vec3(-0.0500, -0.2100, 0.2800),
    vec3( 0.2500,  0.1900, 0.3500),
    vec3(-0.2900,  0.1300, 0.4000),
    vec3( 0.1200, -0.3800, 0.4800),
    vec3(-0.3500, -0.2200, 0.5500),
    vec3( 0.4200,  0.3100, 0.6200),
    vec3(-0.4800,  0.1500, 0.7000),
    vec3( 0.1900, -0.5500, 0.7800),
    vec3(-0.5200, -0.3800, 0.8500),
    vec3( 0.6100,  0.4200, 0.9000),
    vec3(-0.6800,  0.2200, 0.9400),
    vec3( 0.3100, -0.7200, 0.9700),
    vec3(-0.7500, -0.4100, 1.0000)
);

vec3 reconstruct_view_position(vec2 uv, float depth)
{
    vec4 clip;
    clip.xy = uv * 2.0 - 1.0;
    clip.z  = depth * 2.0 - 1.0;
    clip.w  = 1.0;

    vec4 view = sw_InvProjection * clip;
    return view.xyz / view.w;
}

void main()
{
    float depth = texture(SSAO_Depth, v_uv).r;

    // Early exit for skybox/far plane
    if (depth >= 1.0)
    {
        SSAO_Out = 1.0;
        return;
    }

    vec3 position = reconstruct_view_position(v_uv, depth);
    vec3 normal   = normalize(texture(SSAO_Normals, v_uv).xyz * 2.0 - 1.0);

    // 1. Tiling noise vector across the screen (assuming 4x4 noise texture)
    vec2 noise_scale = sw_Resolution / 4.0;
    vec3 random_vec  = texture(SSAO_Noise, v_uv * noise_scale).xyz * 2.0 - 1.0;

    // 2. Build Tangent-Bitangent-Normal (TBN) matrix to orient hemisphere
    vec3 tangent   = normalize(random_vec - normal * dot(random_vec, normal));
    vec3 bitangent = cross(normal, tangent);
    mat3 TBN       = mat3(tangent, bitangent, normal);

    float occlusion = 0.0;

    for (int i = 0; i < SAMPLE_COUNT; ++i)
    {
        // Orient hemisphere sample along local surface normal
        vec3 sample_dir = TBN * samples[i];
        vec3 sample_pos = position + sample_dir * sw_Radius;

        // Project sample point to UV space
        vec4 offset = sw_Projection * vec4(sample_pos, 1.0);
        offset.xyz /= offset.w;
        vec2 sample_uv = offset.xy * 0.5 + 0.5;

        // Skip off-screen samples
        if (sample_uv.x < 0.0 || sample_uv.x > 1.0 ||
            sample_uv.y < 0.0 || sample_uv.y > 1.0)
        {
            continue;
        }

        float sample_depth = texture(SSAO_Depth, sample_uv).r;
        vec3 actual_pos    = reconstruct_view_position(sample_uv, sample_depth);

        // 3. Cosine-weighted occlusion check
        vec3 dir_to_actual = actual_pos - position;
        float dist         = length(dir_to_actual);
        vec3 occluder_dir  = dir_to_actual / dist;

        float cos_theta    = max(0.0, dot(normal, occluder_dir) - sw_Bias);

        // 4. Smooth range attenuation (prevents background objects from casting AO)
        float range_check  = smoothstep(1.0, 0.0, dist / sw_Radius);

        occlusion += cos_theta * range_check;
    }

    // Normalize and invert AO
    float raw_occlusion = (occlusion / float(SAMPLE_COUNT)) * sw_Intensity;
    float ao = 1.0 - raw_occlusion;

    // Clamp and apply exponential power curve to deepen dark spots
    float clamped_ao = clamp(ao, 0.0, 1.0);
    SSAO_Out = pow(clamped_ao, sw_Power);
}