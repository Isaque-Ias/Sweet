#version 460 core

in vec2 v_uv;

layout(location = 0) out float AOY_Out;


// ============================================================
// INPUTS
// ============================================================

uniform sampler2D SSAO_Input;

uniform sampler2D SSAO_Depth;

uniform sampler2D SSAO_Normals;


// ============================================================
// CAMERA
// ============================================================

uniform mat4 sw_InvProjection;


// ============================================================
// SETTINGS
// ============================================================

uniform vec2 sw_Resolution;

uniform int sw_BlurRadius;

uniform float sw_DepthSharpness;

uniform float sw_NormalSharpness;


// ============================================================
// VIEW POSITION RECONSTRUCTION
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
// MAIN
// ============================================================

void main()
{
    vec2 texel_size =
        1.0
        / sw_Resolution;


    // --------------------------------------------------------
    // Center pixel
    // --------------------------------------------------------

    float center_depth =
        texture(
            SSAO_Depth,
            v_uv
        ).r;


    // Background
    if (
        center_depth >= 0.999999
    )
    {
        AOY_Out = 1.0;
        return;
    }


    vec3 center_position =
        reconstruct_view_position(
            v_uv,
            center_depth
        );


    float center_view_depth =
        center_position.z;


    vec3 center_normal =
        texture(
            SSAO_Normals,
            v_uv
        ).xyz;


    center_normal =
        normalize(
            center_normal
            * 2.0
            - 1.0
        );


    float result =
        0.0;


    float weight_sum =
        0.0;


    // --------------------------------------------------------
    // Vertical bilateral blur
    // --------------------------------------------------------

    for (
        int y = -sw_BlurRadius;
        y <= sw_BlurRadius;
        ++y
    )
    {
        vec2 offset =
            vec2(
                0.0,
                float(y)
            )
            * texel_size;


        vec2 sample_uv =
            clamp(
                v_uv
                + offset,
                vec2(0.0),
                vec2(1.0)
            );


        // ----------------------------------------------------
        // AO
        // ----------------------------------------------------

        float sample_ao =
            texture(
                SSAO_Input,
                sample_uv
            ).r;


        // ----------------------------------------------------
        // Depth
        // ----------------------------------------------------

        float sample_depth =
            texture(
                SSAO_Depth,
                sample_uv
            ).r;


        if (
            sample_depth >= 0.999999
        )
        {
            continue;
        }


        vec3 sample_position =
            reconstruct_view_position(
                sample_uv,
                sample_depth
            );


        float sample_view_depth =
            sample_position.z;


        // ----------------------------------------------------
        // Normal
        // ----------------------------------------------------

        vec3 sample_normal =
            texture(
                SSAO_Normals,
                sample_uv
            ).xyz;


        sample_normal =
            normalize(
                sample_normal
                * 2.0
                - 1.0
            );


        // ----------------------------------------------------
        // Spatial Gaussian weight
        // ----------------------------------------------------

        float distance =
            float(y);


        float spatial_weight =
            exp(
                -(
                    distance
                    * distance
                )
                / 8.0
            );


        // ----------------------------------------------------
        // Depth edge weight
        // ----------------------------------------------------

        float depth_difference =
            abs(
                sample_view_depth
                - center_view_depth
            );


        float depth_weight =
            exp(
                -depth_difference
                * sw_DepthSharpness
            );


        // ----------------------------------------------------
        // Normal edge weight
        // ----------------------------------------------------

        float normal_similarity =
            max(
                dot(
                    center_normal,
                    sample_normal
                ),
                0.0
            );


        float normal_weight =
            pow(
                normal_similarity,
                sw_NormalSharpness
            );


        // ----------------------------------------------------
        // Combined weight
        // ----------------------------------------------------

        float weight =
            spatial_weight
            * depth_weight
            * normal_weight;


        result +=
            sample_ao
            * weight;


        weight_sum +=
            weight;
    }


    // --------------------------------------------------------
    // Normalize
    // --------------------------------------------------------

    AOY_Out =
        result
        / max(
            weight_sum,
            0.00001
        );
}