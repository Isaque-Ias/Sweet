#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 Light_Out;

uniform sampler2D Light_Albedo;
uniform sampler2D Light_Normals;
uniform sampler2D Light_Depth;
uniform sampler2D Light_SSAO;

// --- PBR material maps ---
// ORM packing: R = material AO, G = roughness, B = metallic
uniform sampler2D Light_ORM;
uniform sampler2D Light_Emissive;   // RGB = emissive color
uniform sampler2D Light_ClearCoat;  // RGB = clearcoat intensity, A = clearcoat roughness
uniform sampler2D Light_Specular;   // RGB = specular color tint, A = specular factor
uniform sampler2D Light_Transmission; // R = transmission factor

// --- Shadow map (single, no cascades) ---
uniform sampler2D Light_ShadowMap;
uniform mat4 sw_LightView;
uniform mat4 sw_LightProjection;

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

uniform vec3 sw_LightDirection;
uniform vec3 sw_LightColor;
uniform vec3 sw_AmbientColor;

uniform vec2 sw_ShadowMapSize;
uniform float sw_Radius = 1.5;   // PCF sample spread, in texels
uniform float sw_Bias = 0.0015;

// --- PBR parameters (act as multipliers/overrides over sampled maps) ---
uniform float sw_Roughness = 1.0;   // multiplies ORM.g
uniform float sw_Metallic  = 1.0;   // multiplies ORM.b
uniform float sw_Specular  = 1.0;   // scales dielectric reflectance (0.16 * (sw_Specular * SpecularFactor)^2)
uniform float sw_Albedo    = 1.0;   // scales the sampled albedo color

// --- Clear coat ---
uniform float sw_ClearCoat          = 0.0;  // multiplies ClearCoat intensity, 0 = layer disabled
uniform float sw_ClearCoatRoughness = 1.0;  // multiplies ClearCoat roughness

// --- Transmission ---
uniform float sw_Transmission       = 0.0;  // multiplies transmission factor, 0 = disabled
uniform vec3  sw_TransmissionColor  = vec3(1.0);
uniform float sw_Ior                = 0.0;  // Index of Refraction (e.g., 1.5 for glass)

// --- Emissive ---
uniform vec3  sw_EmissiveColor    = vec3(1.0);
uniform float sw_EmissiveStrength = 1.0;

// Reflection probe
uniform samplerCube sw_Skybox;

const float PI = 3.14159265359;

const int PCF_SAMPLES = 16;
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

// Single-map soft PCF shadow
float shadow_factor(vec3 world_position, vec3 normal, vec3 L)
{
    vec4 light_clip = sw_LightProjection * sw_LightView * vec4(world_position, 1.0);
    vec3 shadow_uvz = (light_clip.xyz / light_clip.w) * 0.5 + 0.5;

    if (shadow_uvz.x < 0.0 || shadow_uvz.x > 1.0 ||
        shadow_uvz.y < 0.0 || shadow_uvz.y > 1.0 ||
        shadow_uvz.z > 1.0 || shadow_uvz.z < 0.0)
    {
        return 1.0; // Outside the shadow map bounds -> fully lit
    }

    float bias = max(sw_Bias * (1.0 - dot(normal, L)), sw_Bias * 0.2);
    vec2 texel = sw_Radius / sw_ShadowMapSize;

    float shadow_sum = 0.0;
    for (int i = 0; i < PCF_SAMPLES; ++i)
    {
        vec2 offset = POISSON_DISK[i] * texel;
        float sample_depth = texture(Light_ShadowMap, shadow_uvz.xy + offset).r;
        shadow_sum += (shadow_uvz.z - bias <= sample_depth) ? 1.0 : 0.0;
    }

    return shadow_sum / float(PCF_SAMPLES);
}

// Multi-level Blur Reflection Function
vec3 sample_blurred_reflection(vec3 R, float roughness)
{
    float max_mip = float(textureQueryLevels(sw_Skybox) - 1);
    float target_lod = roughness * max(max_mip, 0.0);

    vec3 up = abs(R.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 Tangent = normalize(cross(up, R));
    vec3 Bitangent = cross(R, Tangent);

    float filter_spread = roughness * roughness * 0.35;

    vec3 blurred_color = vec3(0.0);
    for (int i = 0; i < PCF_SAMPLES; ++i)
    {
        vec2 offset = POISSON_DISK[i] * filter_spread;
        vec3 sampled_dir = normalize(R + Tangent * offset.x + Bitangent * offset.y);
        blurred_color += textureLod(sw_Skybox, sampled_dir, target_lod).rgb;
    }

    return blurred_color / float(PCF_SAMPLES);
}

// Cook-Torrance BRDF Components
float distribution_ggx(vec3 N, vec3 H, float roughness)
{
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;
    return a2 / max(denom, 1e-6);
}

float geometry_schlick_ggx(float NdotV, float roughness)
{
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;
    return NdotV / (NdotV * (1.0 - k) + k);
}

float geometry_smith(float NdotV, float NdotL, float roughness)
{
    return geometry_schlick_ggx(NdotV, roughness) * geometry_schlick_ggx(NdotL, roughness);
}

vec3 fresnel_schlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

void main()
{
    float depth = texture(Light_Depth, v_uv).r;
    if (depth >= 1.0)
    {
        Light_Out = vec4(0.0);
        return;
    }

    // --- 1. Read Base Surface Maps & Multipliers ---
    vec3 albedo = texture(Light_Albedo, v_uv).rgb * sw_Albedo;
    vec3 normal = normalize(texture(Light_Normals, v_uv).rgb * 2.0 - 1.0);

    // ORM: R = Material AO, G = Roughness, B = Metallic
    vec3 orm = texture(Light_ORM, v_uv).rgb;
    float material_ao = orm.r;
    float roughness   = clamp(orm.g * sw_Roughness, 0.045, 1.0);
    float metallic    = clamp(orm.b * sw_Metallic, 0.0, 1.0);

    float screen_ao = texture(Light_SSAO, v_uv).r;
    float ao = material_ao * screen_ao;

    // --- 2. Read Specular Map & Multipliers ---
    vec4 spec_sample = texture(Light_Specular, v_uv);
    vec3 specular_color_tint = spec_sample.rgb;
    float specular_map_factor = spec_sample.a;

    float dielectric_specular = 0.16 * pow(sw_Specular * specular_map_factor, 2.0);
    vec3 F0 = mix(dielectric_specular * specular_color_tint, albedo, metallic);

    // --- 3. Read Emissive Map & Multipliers ---
    vec3 emissive = texture(Light_Emissive, v_uv).rgb * sw_EmissiveColor * sw_EmissiveStrength;

    // --- 4. Read Clearcoat Map & Multipliers ---
    vec4 clearcoat_sample = texture(Light_ClearCoat, v_uv);
    float clearcoat             = clamp(clearcoat_sample.r * sw_ClearCoat, 0.0, 1.0);
    float clearcoat_roughness = clamp(clearcoat_sample.a * sw_ClearCoatRoughness, 0.045, 1.0);

    // --- 5. Read Transmission Map & Multipliers ---
    float transmission = 0.0;//clamp(texture(Light_Transmission, v_uv).r * sw_Transmission, 0.0, 1.0);

    // --- 6. Geometry & Vectors ---
    vec3 view_position = reconstruct_view_position(v_uv, depth);
    vec4 world_position4 = sw_InvView * vec4(view_position, 1.0);
    vec3 world_position = world_position4.xyz / world_position4.w;

    vec3 N = normal;
    vec3 V = normalize(mat3(sw_InvView) * normalize(-view_position)); // world-space
    vec3 L = normalize(-sw_LightDirection);
    vec3 H = normalize(V + L);

    float NdotV = max(dot(N, V), 1e-4);
    float NdotL = max(dot(N, L), 0.0);
    float VdotH = max(dot(V, H), 0.0);

    float shadow = shadow_factor(world_position, normal, L);

    // --- 7. Base Layer Cook-Torrance Direct Lighting ---
    float D = distribution_ggx(N, H, roughness);
    float G = geometry_smith(NdotV, NdotL, roughness);
    vec3 F  = fresnel_schlick(VdotH, F0);

    vec3 specular = (D * G * F) / max(4.0 * NdotV * NdotL, 1e-4);
    
    // Energy conservation: Metals and Transmissive surfaces don't have standard diffuse
    vec3 kD = (vec3(1.0) - F) * (1.0 - metallic) * (1.0 - transmission);
    vec3 diffuse = kD * albedo / PI;

    // --- 8. Clearcoat Layer Direct Lighting ---
    float Dc = distribution_ggx(N, H, clearcoat_roughness);
    float Gc = geometry_smith(NdotV, NdotL, clearcoat_roughness);
    vec3 Fc0 = vec3(0.04);
    vec3 Fc_raw = fresnel_schlick(VdotH, Fc0);
    vec3 Fc = Fc_raw * clearcoat;

    vec3 clearcoat_specular = vec3((Dc * Gc) / max(4.0 * NdotV * NdotL, 1e-4)) * Fc;
    vec3 base_attenuation = vec3(1.0) - Fc;

    vec3 direct = (diffuse + specular) * base_attenuation * sw_LightColor * NdotL * shadow
                + clearcoat_specular * sw_LightColor * NdotL * shadow;

    // --- 9. Ambient, Reflection & Transmission ---
    vec3 R = reflect(-V, N);
    vec3 reflection = sample_blurred_reflection(R, roughness);
    vec3 reflection_term = reflection * F * base_attenuation * (1.0 - transmission);

    vec3 reflection_clearcoat = sample_blurred_reflection(R, clearcoat_roughness) * Fc;

    vec3 ambient = albedo * sw_AmbientColor * ao * (1.0 - metallic) * (1.0 - transmission) * base_attenuation;

    // Transmission Refraction Calculation
    float eta = 1.0 / sw_Ior; // Air to material IOR ratio
    vec3 R_trans = refract(-V, N, eta);
    vec3 transmitted_env = sample_blurred_reflection(R_trans, roughness);
    vec3 transmission_term = transmitted_env * albedo * sw_TransmissionColor * transmission * (1.0 - metallic);

    // --- Output Composite ---
    Light_Out = vec4(ambient + direct + reflection_term + reflection_clearcoat + transmission_term + emissive, 1.0);
}