#version 330
uniform samplerCube sw_Skybox;
uniform sampler2D bgLight;

in vec3 v_dir;
in vec2 v_uv;

out vec4 bgOut;

void main() {
    vec4 baseColor = texture(sw_Skybox, normalize(v_dir));
    vec4 lightColor = texture(bgLight, v_uv);
    
    // Blend light color OVER base color using lightColor's alpha
    vec3 blendedRGB = mix(baseColor.rgb, lightColor.rgb, lightColor.a);
    
    // Preserve base alpha (or mix alphas: lightColor.a + baseColor.a * (1.0 - lightColor.a))
    bgOut = vec4(blendedRGB, baseColor.a);
}