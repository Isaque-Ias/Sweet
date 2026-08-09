#version 430 core

layout(location = 0) out vec4 FragColor;

in vec2 v_uv;

uniform sampler2D GBuffer_Albedo;
uniform sampler2D GBuffer_Normals;

uniform vec3 u_light_direction;
uniform vec3 u_light_color;

void main()
{
    vec3 albedo = texture(GBuffer_Albedo, v_uv).rgb;

    vec3 normal = texture(GBuffer_Normals, v_uv).rgb;

    // Decode normal from [0,1] back to [-1,1].
    normal = normalize(normal * 2.0 - 1.0);

    vec3 light_direction = normalize(-u_light_direction);

    float NdotL = max(dot(normal, light_direction), 0.0);

    vec3 lighting =
        albedo *
        u_light_color *
        NdotL;

    FragColor = vec4(lighting, 1.0);
}