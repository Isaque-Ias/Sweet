#version 460 core

in vec2 v_uv;

layout(location = 0) out float SSAO_Out;


// ============================================================
// INPUTS
// ============================================================

uniform sampler2D SSAO_Depth;
uniform sampler2D SSAO_Normals;
uniform sampler2D SSAO_Noise;


// ============================================================
// CAMERA
// ============================================================

uniform mat4 sw_Projection;
uniform mat4 sw_InvProjection;

uniform vec2 sw_Resolution;


// ============================================================
// SSAO SETTINGS
// ============================================================

uniform float sw_Radius;
uniform float sw_Bias;

uniform float sw_Intensity;
uniform float sw_Power;


// ============================================================
// SAMPLE KERNEL
// ============================================================

const int SAMPLE_COUNT = 32;

const vec3 samples[SAMPLE_COUNT] = vec3[]
(
    vec3( 0.5381,  0.1856,  0.4319),
    vec3( 0.1379,  0.2486,  0.4430),
    vec3( 0.3371,  0.5679,  0.0057),
    vec3(-0.6999, -0.0451, -0.0019),
    vec3( 0.0689, -0.1598, -0.8547),
    vec3( 0.0560,  0.0069, -0.1843),
    vec3(-0.0146,  0.1402,  0.0762),
    vec3( 0.0100, -0.1924, -0.0344),
    vec3(-0.3577, -0.5301, -0.4358),
    vec3(-0.3169,  0.1063,  0.0158),
    vec3( 0.0103, -0.5869,  0.0046),
    vec3(-0.0897, -0.4940,  0.3287),
    vec3( 0.7119, -0.0154,  0.0918),
    vec3(-0.0533,  0.0596, -0.5411),
    vec3( 0.0352, -0.0631,  0.5460),
    vec3(-0.4776,  0.2847, -0.0271),
    vec3(-0.1590, -0.1467,  0.1405),
    vec3( 0.1205, -0.1980,  0.2585),
    vec3( 0.1827,  0.1125,  0.3046),
    vec3(-0.0947,  0.3210,  0.2073),
    vec3( 0.2557, -0.0941,  0.3711),
    vec3(-0.2911,  0.1027,  0.3328),
    vec3( 0.0834,  0.3917,  0.1419),
    vec3(-0.4012, -0.1528,  0.2270),
    vec3( 0.3910,  0.2100,  0.1100),
    vec3(-0.2110,  0.3870,  0.0600),
    vec3( 0.3120, -0.2760,  0.1500),
    vec3(-0.1180, -0.3910,  0.1300),
    vec3( 0.1890,  0.0920,  0.4300),
    vec3(-0.2700,  0.1910,  0.2900),
    vec3( 0.0500, -0.1200,  0.4700),
    vec3(-0.0900,  0.0300,  0.5100)
);


// ============================================================
// DEPTH RECONSTRUCTION
// ============================================================

vec3 reconstruct_view_position(
    vec2 uv,
    float depth
)
{
    vec4 clip;

    clip.xy =
        uv * 2.0
        - 1.0;

    clip.z =
        depth * 2.0
        - 1.0;

    clip.w =
        1.0;


    vec4 view =
        sw_InvProjection
        * clip;


    return
        view.xyz
        / view.w;
}


// ============================================================
// TBN CONSTRUCTION
// ============================================================

mat3 create_tbn(
    vec3 normal,
    vec3 random_vec
)
{
    vec3 tangent =
        random_vec
        - normal
        * dot(
            random_vec,
            normal
        );


    tangent =
        normalize(
            tangent
        );


    vec3 bitangent =
        normalize(
            cross(
                normal,
                tangent
            )
        );


    return mat3(
        tangent,
        bitangent,
        normal
    );
}


// ============================================================
// MAIN
// ============================================================

void main()
{
    // --------------------------------------------------------
    // Current pixel depth
    // --------------------------------------------------------

    float depth =
        texture(
            SSAO_Depth,
            v_uv
        ).r;


    // Background / far plane
    if (depth >= 0.999999)
    {
        SSAO_Out = 1.0;
        return;
    }


    // --------------------------------------------------------
    // Reconstruct view-space position
    // --------------------------------------------------------

    vec3 position =
        reconstruct_view_position(
            v_uv,
            depth
        );


    // --------------------------------------------------------
    // Read view-space normal
    // --------------------------------------------------------

    vec3 normal =
        texture(
            SSAO_Normals,
            v_uv
        ).xyz;


    normal =
        normal * 2.0
        - 1.0;


    normal =
        normalize(
            normal
        );


    // --------------------------------------------------------
    // Random kernel rotation
    // --------------------------------------------------------

    vec2 noise_scale =
        sw_Resolution
        / 4.0;


    vec3 random_vec =
        texture(
            SSAO_Noise,
            v_uv
            * noise_scale
        ).xyz;


    random_vec =
        random_vec * 2.0
        - 1.0;


    random_vec =
        normalize(
            random_vec
        );


    // --------------------------------------------------------
    // Build local tangent space
    // --------------------------------------------------------

    mat3 TBN =
        create_tbn(
            normal,
            random_vec
        );


    float occlusion =
        0.0;


    int valid_samples =
        0;


    // --------------------------------------------------------
    // Sample hemisphere
    // --------------------------------------------------------

    for (
        int i = 0;
        i < SAMPLE_COUNT;
        ++i
    )
    {
        // ----------------------------------------------------
        // Orient sample along surface normal
        // ----------------------------------------------------

        vec3 sample_vector =
            TBN
            * samples[i];


        // ----------------------------------------------------
        // Bias samples toward the center
        // ----------------------------------------------------

        float scale =
            float(i)
            / float(SAMPLE_COUNT);


        scale =
            mix(
                0.1,
                1.0,
                scale
                * scale
            );


        // ----------------------------------------------------
        // Generate hypothetical sample position
        // ----------------------------------------------------

        vec3 sample_position =
            position
            + sample_vector
            * sw_Radius
            * scale;


        // ----------------------------------------------------
        // Project sample position
        // ----------------------------------------------------

        vec4 projected =
            sw_Projection
            * vec4(
                sample_position,
                1.0
            );


        // Sample behind camera
        if (
            projected.w <= 0.0
        )
        {
            continue;
        }


        projected.xyz /=
            projected.w;


        vec2 sample_uv =
            projected.xy
            * 0.5
            + 0.5;


        // ----------------------------------------------------
        // Reject off-screen samples
        // ----------------------------------------------------

        if (
            sample_uv.x < 0.0 ||
            sample_uv.x > 1.0 ||
            sample_uv.y < 0.0 ||
            sample_uv.y > 1.0
        )
        {
            continue;
        }


        // ----------------------------------------------------
        // Read depth at projected sample position
        // ----------------------------------------------------

        float sample_depth =
            texture(
                SSAO_Depth,
                sample_uv
            ).r;


        // Background does not occlude
        if (
            sample_depth >= 0.999999
        )
        {
            continue;
        }


        vec3 actual_position =
            reconstruct_view_position(
                sample_uv,
                sample_depth
            );


        // ----------------------------------------------------
        // Range attenuation
        // ----------------------------------------------------

        float depth_difference =
            abs(
                position.z
                - actual_position.z
            );


        float range_check =
            smoothstep(
                1.0,
                0.0,
                depth_difference
                / sw_Radius
            );


        // ----------------------------------------------------
        // Occlusion test
        //
        // Standard OpenGL view space:
        //
        // Camera looks toward -Z.
        //
        // A larger Z value is closer to the camera.
        // ----------------------------------------------------

        float occluded =
            actual_position.z
            >= sample_position.z
            + sw_Bias
            ? 1.0
            : 0.0;


        occlusion +=
            occluded
            * range_check;


        valid_samples++;
    }


    // --------------------------------------------------------
    // Normalize
    // --------------------------------------------------------

    if (
        valid_samples > 0
    )
    {
        occlusion /=
            float(
                valid_samples
            );
    }


    // --------------------------------------------------------
    // Convert occlusion to AO
    // --------------------------------------------------------

    float ao =
        1.0
        - occlusion
        * sw_Intensity;


    ao =
        clamp(
            ao,
            0.0,
            1.0
        );


    SSAO_Out =
        pow(
            ao,
            sw_Power
        );
}