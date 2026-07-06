#version 430 core

in vec2 v_texcoord;
in vec4 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;
in vec3 v_cam_pos;

uniform sampler2D sw_texture;
out vec4 FragColor;

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

    vec3 lightingResult = ambient + diffuse;
    FragColor = vec4(lightingResult * texColor.rgb, texColor.a);
}