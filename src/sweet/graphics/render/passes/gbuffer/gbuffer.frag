#version 460 core

layout(location = 0) out vec4 GBuffer_Albedo;   // RGB: Base Color, A: Unused / Alpha
layout(location = 1) out vec4 GBuffer_Normals;  // RGB: Encoded Normal
layout(location = 2) out vec4 GBuffer_ORM;      // R: Occlusion, G: Roughness, B: Metalness
layout(location = 3) out vec4 GBuffer_Specular; // RGB: Specular Color, A: Specular Factor
layout(location = 4) out vec4 GBuffer_Emissive; // RGB: Emissive Color
layout(location = 5) out vec4 GBuffer_Clearcoat;// RGB: Clearcoat Intensity, A: Clearcoat Roughness

layout(std430, binding = 6) readonly buffer sw_Textures { uint pixels[]; };

in vec3 v_world_position;
in vec3 v_world_normal;
in vec2 v_texcoord;
in vec4 v_view_position;
flat in uint v_material_id;

struct Range { 
    uint offset; 
    uint count; 
};

struct TextureRef { 
    Range range; 
    uint width; 
    uint height; 
};

// Layout matching the python upload payload layout precisely
struct MaterialObject {
    TextureRef albedo;
    TextureRef orm;
    TextureRef specular;
    TextureRef emissive;
    TextureRef clearcoat;
    TextureRef clearcoatRoughness;
    
    vec4 factors;               // x: metallic, y: roughness, z: occlusion_strength, w: specular_factor
    vec4 emissiveFactor;        // rgb: emissive_factor, a: unused
    vec4 specularColorFactor;   // rgb: specular_color_factor, a: unused
    vec4 clearcoatFactors;      // x: clearcoat_factor, y: clearcoat_roughness_factor, zw: unused
    vec4 albedoFactor;          // rgba: base_color_factor (offset 160)
};

layout(std430, binding = 5) readonly buffer sw_Materials {
    MaterialObject material[];
};

bool hasTexture(TextureRef ref) { 
    return ref.range.count > 0u; 
}

vec4 sampleTextureRef(TextureRef ref, vec2 uv)
{
    vec2 wrapped = fract(uv);
    wrapped.y = 1.0 - wrapped.y; // glTF V-down vs. V-up pixel buffer alignment

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

    // --- 1. Albedo / Base Color ---
    vec4 albedoSample = hasTexture(mat.albedo)
        ? sampleTextureRef(mat.albedo, v_texcoord)
        : vec4(1.0); // Fallback to 1.0 so albedoFactor modulates correctly
    vec4 finalAlbedo = albedoSample * mat.albedoFactor;

    // --- 2. Occlusion, Roughness, Metallic (ORM) ---
    vec3 ormSample = hasTexture(mat.orm)
        ? sampleTextureRef(mat.orm, v_texcoord).rgb
        : vec3(1.0);

    float occlusion = ormSample.r * mat.factors.z;
    float roughness = ormSample.g * mat.factors.y;
    float metalness = ormSample.b * mat.factors.x;

    // --- 3. Specular ---
    vec4 specularSample = hasTexture(mat.specular)
        ? sampleTextureRef(mat.specular, v_texcoord)
        : vec4(1.0);
    vec3 specularColor = specularSample.rgb * mat.specularColorFactor.rgb;
    float specularFactor = specularSample.a * mat.factors.w;

    // --- 4. Emissive ---
    vec3 emissive = hasTexture(mat.emissive)
        ? sampleTextureRef(mat.emissive, v_texcoord).rgb * mat.emissiveFactor.rgb
        : mat.emissiveFactor.rgb;

    // --- 5. Clearcoat & Clearcoat Roughness ---
    float clearcoatSample = hasTexture(mat.clearcoat)
        ? sampleTextureRef(mat.clearcoat, v_texcoord).r
        : 1.0;
    float clearcoatFactor = clearcoatSample * mat.clearcoatFactors.x;

    float clearcoatRoughnessSample = hasTexture(mat.clearcoatRoughness)
        ? sampleTextureRef(mat.clearcoatRoughness, v_texcoord).g
        : 1.0;
    float clearcoatRoughnessFactor = clearcoatRoughnessSample * mat.clearcoatFactors.y;

    // --- 6. Normal Encoding ---
    vec3 normal = normalize(v_world_normal);
    vec3 encoded_normal = normal * 0.5 + 0.5;

    // --- Output Assignments ---
    GBuffer_Albedo    = finalAlbedo;
    GBuffer_Normals   = vec4(encoded_normal, 1.0);
    GBuffer_ORM       = vec4(occlusion, roughness, metalness, 1.0);
    GBuffer_Specular  = vec4(specularColor, specularFactor);
    GBuffer_Emissive  = vec4(emissive, 1.0);
    GBuffer_Clearcoat = vec4(vec3(clearcoatFactor), clearcoatRoughnessFactor);
}