#version 460 core

layout(location = 0) out vec4 GBuffer_Albedo;
layout(location = 1) out vec4 GBuffer_Normals;
layout(location = 2) out vec4 GBuffer_ORM;
layout(location = 3) out vec4 GBuffer_Specular;
layout(location = 4) out vec4 GBuffer_Emissive;

layout(std430, binding = 6) readonly buffer sw_Textures { uint pixels[]; };

in vec3 v_world_position;
in vec3 v_world_normal;
in vec2 v_texcoord;
in vec4 v_view_position;
flat in uint v_material_id;

struct Range { uint offset; uint count; };
struct TextureRef { Range range; uint width; uint height; };

struct MaterialObject {
    TextureRef albedo;
    TextureRef orm;
    TextureRef specular;
    TextureRef emissive;
    vec4 factors;
    vec4 emissiveFactor;
    vec4 specularColorFactor;
};

layout(std430, binding = 5) readonly buffer sw_Materials {
    MaterialObject material[];
};

bool hasTexture(TextureRef ref) { return ref.range.count > 0u; }

vec4 sampleTextureRef(TextureRef ref, vec2 uv)
{
    vec2 wrapped = fract(uv);
    wrapped.y = 1.0 - wrapped.y; // glTF V-down vs. our V-up pixel buffer

    uint x = min(uint(wrapped.x * float(ref.width)),  ref.width  - 1u);
    uint y = min(uint(wrapped.y * float(ref.height)), ref.height - 1u);

    uint pixelIndex = ref.range.offset + y * ref.width + x;
    if (pixelIndex >= ref.range.offset + ref.range.count) {
        return vec4(1.0, 0.0, 1.0, 1.0); // out-of-range flag
    }
    return unpackUnorm4x8(pixels[pixelIndex]);
}

void main()
{
    MaterialObject mat = material[v_material_id];

    vec3 albedo = hasTexture(mat.albedo)
        ? sampleTextureRef(mat.albedo, v_texcoord).rgb
        : vec3(0.8);

    vec3 ormSample = hasTexture(mat.orm)
        ? sampleTextureRef(mat.orm, v_texcoord).rgb
        : vec3(1.0); // no map => factors alone decide

    float occlusion = ormSample.r * mat.factors.z;
    float roughness = ormSample.g * mat.factors.y;
    float metalness = ormSample.b * mat.factors.x;

    vec4 specularSample = hasTexture(mat.specular)
        ? sampleTextureRef(mat.specular, v_texcoord)
        : vec4(1.0);
    vec3 specularColor = specularSample.rgb * mat.specularColorFactor.rgb;
    float specularFactor = specularSample.a * mat.factors.w;

    vec3 emissive = hasTexture(mat.emissive)
        ? sampleTextureRef(mat.emissive, v_texcoord).rgb * mat.emissiveFactor.rgb
        : mat.emissiveFactor.rgb;

    vec3 normal = normalize(v_world_normal);
    vec3 encoded_normal = normal * 0.5 + 0.5;

    GBuffer_Albedo   = vec4(albedo, 1.0);
    GBuffer_Normals  = vec4(encoded_normal, 1.0);
    GBuffer_ORM      = vec4(occlusion, roughness, metalness, 1.0);
    GBuffer_Specular = vec4(specularColor, specularFactor);
    GBuffer_Emissive = vec4(emissive, 1.0);
}