#version 460 core

in vec2 v_uv;

layout(location = 0) out float out_ssao;

uniform sampler2D sw_Depth;
uniform sampler2D sw_Normals;

uniform mat4 sw_Projection;
uniform mat4 sw_InvProjection;

uniform vec2 sw_Resolution;

uniform float sw_Radius;
uniform float sw_Bias;

const int SAMPLE_COUNT = 16;

const vec3 samples[SAMPLE_COUNT] = vec3[](
    vec3( 0.5381,  0.1856,  0.4319),
    vec3( 0.1379,  0.2486,  0.4430),
    vec3( 0.3371,  0.5679,  0.0057),
    vec3(-0.6999, -0.0451,  0.0019),

    vec3( 0.0689, -0.1598,  0.8547),
    vec3( 0.0560,  0.0069,  0.1843),
    vec3(-0.0146,  0.1402,  0.0762),
    vec3( 0.0100, -0.1924, -0.0344),

    vec3(-0.3577, -0.5301, -0.4358),
    vec3(-0.3169,  0.1063,  0.0158),
    vec3( 0.0103, -0.5869,  0.0046),
    vec3(-0.0897, -0.4940,  0.3287),

    vec3( 0.7119, -0.0154, -0.0918),
    vec3(-0.0533,  0.0596, -0.5411),
    vec3( 0.0352, -0.0631,  0.5460),
    vec3(-0.4776,  0.2847, -0.0271)
);

vec3 reconstruct_view_position(vec2 uv, float depth)
{
    vec4 clip;

    clip.xy =
        uv * 2.0 - 1.0;

    clip.z =
        depth * 2.0 - 1.0;

    clip.w = 1.0;

    vec4 view =
        sw_InvProjection * clip;

    return view.xyz / view.w;
}

void main()
{
    float depth =
        texture(sw_Depth, v_uv).r;

    if (depth >= 1.0)
    {
        out_ssao = 1.0;
        return;
    }

    vec3 position =
        reconstruct_view_position(
            v_uv,
            depth
        );

    vec3 normal =
        texture(sw_Normals, v_uv).xyz;

    normal =
        normalize(normal * 2.0 - 1.0);

    float occlusion = 0.0;

    for (int i = 0; i < SAMPLE_COUNT; ++i)
    {
        vec3 sample_direction =
            samples[i];

        /*
         * Orient samples approximately around
         * the surface normal.
         */
        if (dot(sample_direction, normal) < 0.0)
            sample_direction *= -1.0;

        vec3 sample_position =
            position +
            sample_direction * sw_Radius;

        vec4 projected =
            sw_Projection *
            vec4(sample_position, 1.0);

        projected.xyz /=
            projected.w;

        vec2 sample_uv =
            projected.xy * 0.5 + 0.5;

        if (sample_uv.x < 0.0 ||
            sample_uv.x > 1.0 ||
            sample_uv.y < 0.0 ||
            sample_uv.y > 1.0)
        {
            continue;
        }

        float sample_depth =
            texture(sw_Depth, sample_uv).r;

        vec3 actual_position =
            reconstruct_view_position(
                sample_uv,
                sample_depth
            );

        float range =
            smoothstep(
                0.0,
                1.0,
                sw_Radius /
                abs(position.z - actual_position.z)
            );

        if (actual_position.z >
            sample_position.z + sw_Bias)
        {
            occlusion += range;
        }
    }

    float ao =
        1.0 -
        occlusion / float(SAMPLE_COUNT);

    out_ssao =
        clamp(ao, 0.0, 1.0);
}