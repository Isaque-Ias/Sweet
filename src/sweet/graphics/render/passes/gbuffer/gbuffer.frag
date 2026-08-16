#version 460 core

layout(location = 0) out vec4 GBuffer_Albedo;
layout(location = 1) out vec4 GBuffer_Normals;

in vec3 v_world_position;
in vec3 v_world_normal;
in vec2 v_texcoord;
in vec4 v_view_position;

void main()
{
    /*
     * For now, use a constant material color.
     *
     * Later this can become:
     *
     * material.albedo
     * texture(material.albedo_texture, v_texcoord)
     * etc.
     */
    vec3 albedo = vec3(0.8, 0.8, 0.8);

    vec3 normal =
        normalize(v_world_normal);

    /*
     * Encode [-1,1] normal into [0,1].
     */
    vec3 encoded_normal =
        normal * 0.5 + 0.5;

    GBuffer_Albedo =
        vec4(albedo, 1.0);

    GBuffer_Normals =
        vec4(encoded_normal, 1.0);
}