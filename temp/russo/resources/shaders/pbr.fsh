#version 430 core

in vec2 v_texcoord;
in vec4 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;
in vec3 v_cam_pos;

uniform sampler2D sw_texture;
out vec4 FragColor;

float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float nom   = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;

    return nom / denom;
}

// Schlick-GGX Geometry Function
float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;

    float nom   = NdotV;
    float denom = NdotV * (1.0 - k) + k;

    return nom / denom;
}

// Fresnel-Schlick Equation
vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

void main()
{
    // Pure World Space coordinates
    vec3 lightPos = v_cam_pos;
    vec3 lightColor = vec3(1.0);
    float ambientStrength = 0.25;

    vec4 texColor = texture(sw_texture, v_texcoord) * v_color;
    if (texColor.a < 0.9) {
        discard;
    }
    vec3 ambient = ambientStrength * lightColor;

    vec3 norm = normalize(v_normal);
    vec3 lightDir = normalize(lightPos - v_frag_pos);
    
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    PBR = DistributionGGX() * ;

    vec3 lightingResult = ambient + diffuse;
    FragColor = vec4(lightingResult * texColor.rgb, texColor.a);
}