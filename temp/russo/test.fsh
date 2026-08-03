#version 460 core

in vec3 v_WorldPos;
in vec3 v_Normal;
in vec2 v_UV;

out vec4 FragColor;

void main() {
    // Simple directional light direction
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
    
    // Ambient light baseline
    vec3 ambient = vec3(0.1);
    
    // Diffuse lighting (Lambertian reflection)
    float diff = max(dot(v_Normal, lightDir), 0.0);
    vec3 diffuse = vec3(0.8) * diff;

    // Base color (gray mesh tint)
    vec3 baseColor = vec3(0.7, 0.7, 0.7) * v_UV.x;
    
    vec3 result = (ambient + diffuse) * baseColor;
    FragColor = vec4(result, 1.0);
}