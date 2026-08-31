#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 Light_Out;

uniform sampler2D Light_Albedo;
uniform sampler2D Light_Normals;
uniform sampler2D Light_Depth;
uniform sampler2D Light_SSAO;
uniform sampler2D Light_ShadowMap;

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

uniform mat4 sw_LightView;
uniform mat4 sw_LightProjection;

uniform vec3 sw_LightDirection;
uniform vec3 sw_LightColor;
uniform vec3 sw_AmbientColor;

uniform vec2 sw_ShadowMapSize;
uniform float sw_LightSize = 8.0;

const int PCSS_SAMPLES = 16;
const vec2 POISSON_DISK[16] = vec2[](
    vec2(-0.94201624, -0.39906216), vec2(0.94558609, -0.26889616),
    vec2(-0.09418410, -0.92938870), vec2(0.34495938,  0.29387760),
    vec2(-0.91588581,  0.45771432), vec2(-0.81544232, -0.87912464),
    vec2(-0.38277543,  0.27676845), vec2(0.97484398,  0.75648377),
    vec2(0.44323325, -0.97511554), vec2(0.53742981, -0.47373420),
    vec2(-0.26496911, -0.41893023), vec2(0.79197514,  0.19090160),
    vec2(-0.24188840,  0.99706507), vec2(-0.81409955,  0.91437590),
    vec2(0.19984126,  0.78641367), vec2(0.14383161, -0.14100790)
);

vec3 reconstruct_view_position(vec2 uv, float depth)
{
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 view = sw_InvProjection * clip;
    return view.xyz / view.w;
}

float find_blocker_depth(vec3 shadow_uvz, float bias, float search_radius)
{
    float blocker_sum = 0.0;
    int num_blockers = 0;

    for (int i = 0; i < PCSS_SAMPLES; ++i)
    {
        vec2 offset = POISSON_DISK[i] * search_radius;
        float sample_depth = texture(Light_ShadowMap, shadow_uvz.xy + offset).r;

        if (sample_depth < shadow_uvz.z - bias)
        {
            blocker_sum += sample_depth;
            num_blockers++;
        }
    }

    if (num_blockers == 0) 
        return -1.0;

    return blocker_sum / float(num_blockers);
}

float shadow_factor(vec3 world_position, vec3 normal, vec3 L)
{
    vec4 light_clip = sw_LightProjection * sw_LightView * vec4(world_position, 1.0);
    light_clip.xyz /= light_clip.w;
    vec3 shadow_uvz = light_clip.xyz * 0.5 + 0.5;

    // Outside light bounds -> fully lit
    if (shadow_uvz.x < 0.0 || shadow_uvz.x > 1.0 ||
        shadow_uvz.y < 0.0 || shadow_uvz.y > 1.0 ||
        shadow_uvz.z > 1.0 || shadow_uvz.z < 0.0)
    {
        return 1.0;
    }

    float bias = max(0.002 * (1.0 - dot(normal, L)), 0.0002);

    float search_radius = sw_LightSize / sw_ShadowMapSize.x;
    float avg_blocker_depth = find_blocker_depth(shadow_uvz, bias, search_radius);

    if (avg_blocker_depth < 0.0)
        return 1.0; 

    float receiver_depth = shadow_uvz.z;
    float penumbra = max(0.0, (receiver_depth - avg_blocker_depth) / avg_blocker_depth);
    float filter_radius = penumbra * sw_LightSize / sw_ShadowMapSize.x;

    float shadow_sum = 0.0;
    for (int i = 0; i < PCSS_SAMPLES; ++i)
    {
        vec2 offset = POISSON_DISK[i] * filter_radius;
        float sample_depth = texture(Light_ShadowMap, shadow_uvz.xy + offset).r;
        shadow_sum += (receiver_depth - bias <= sample_depth) ? 1.0 : 0.0;
    }

    return shadow_sum / float(PCSS_SAMPLES);
}

void main()
{
    float depth = texture(Light_Depth, v_uv).r;
    if (depth >= 1.0)
    {
        Light_Out = vec4(0.0);
        return;
    }

    vec3 albedo = texture(Light_Albedo, v_uv).rgb;
    vec3 normal = normalize(texture(Light_Normals, v_uv).rgb * 2.0 - 1.0);
    float ao = texture(Light_SSAO, v_uv).r;

    vec3 view_position = reconstruct_view_position(v_uv, depth);
    vec4 world_position4 = sw_InvView * vec4(view_position, 1.0);
    vec3 world_position = world_position4.xyz / world_position4.w;

    vec3 L = normalize(-sw_LightDirection);
    float NdotL = max(dot(normal, L), 0.0);

    float shadow = shadow_factor(world_position, normal, L);

    vec3 ambient = albedo * sw_AmbientColor * ao;
    vec3 diffuse = albedo * sw_LightColor * NdotL * shadow;

    Light_Out = vec4(ambient + diffuse, 1.0);
}