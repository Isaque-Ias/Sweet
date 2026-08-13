#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 out_color;

uniform sampler2D sw_Albedo;
uniform sampler2D sw_Normals;
uniform sampler2D sw_Depth;
uniform sampler2D sw_SSAO;
uniform sampler2D sw_ShadowMap;

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

uniform mat4 sw_LightView;
uniform mat4 sw_LightProjection;

uniform vec3 sw_LightDirection;
uniform vec3 sw_LightColor;

uniform vec3 sw_CameraPosition;

uniform float sw_AmbientStrength;

vec3 reconstruct_view_position(
    vec2 uv,
    float depth
)
{
    vec4 clip =
        vec4(
            uv * 2.0 - 1.0,
            depth * 2.0 - 1.0,
            1.0
        );

    vec4 view =
        sw_InvProjection *
        clip;

    return view.xyz / view.w;
}

float shadow_factor(vec3 world_position)
{
    vec4 light_clip =
        sw_LightProjection *
        sw_LightView *
        vec4(world_position, 1.0);

    light_clip.xyz /=
        light_clip.w;

    vec3 shadow_uvz =
        light_clip.xyz * 0.5 + 0.5;

    if (shadow_uvz.x < 0.0 ||
        shadow_uvz.x > 1.0 ||
        shadow_uvz.y < 0.0 ||
        shadow_uvz.y > 1.0)
    {
        return 1.0;
    }

    if (shadow_uvz.z > 1.0)
        return 1.0;

    float shadow_depth =
        texture(
            sw_ShadowMap,
            shadow_uvz.xy
        ).r;

    float bias = 0.002;

    return
        shadow_uvz.z - bias <= shadow_depth
        ? 1.0
        : 0.0;
}

void main()
{
    float depth =
        texture(sw_Depth, v_uv).r;

    /*
     * Nothing was rendered here.
     */
    if (depth >= 1.0)
    {
        out_color =
            vec4(0.0);

        return;
    }

    vec3 albedo =
        texture(
            sw_Albedo,
            v_uv
        ).rgb;

    vec3 normal =
        texture(
            sw_Normals,
            v_uv
        ).rgb;

    normal =
        normalize(
            normal * 2.0 - 1.0
        );

    float ao =
        texture(
            sw_SSAO,
            v_uv
        ).r;

    vec3 view_position =
        reconstruct_view_position(
            v_uv,
            depth
        );

    vec4 world_position4 =
        sw_InvView *
        vec4(view_position, 1.0);

    vec3 world_position =
        world_position4.xyz /
        world_position4.w;

    /*
     * Light direction points FROM the surface
     * toward the light.
     */
    vec3 L =
        normalize(-sw_LightDirection);

    float NdotL =
        max(
            dot(normal, L),
            0.0
        );

    float shadow =
        shadow_factor(
            world_position
        );

    vec3 ambient =
        albedo *
        sw_AmbientStrength *
        ao;

    vec3 diffuse =
        albedo *
        sw_LightColor *
        NdotL *
        shadow;

    vec3 color =
        ambient +
        diffuse;

    out_color =
        vec4(color, 1.0);
}