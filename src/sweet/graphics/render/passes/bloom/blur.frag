#version 330 core
out vec4 BloomBlur_Out;
in vec2 v_uv;

uniform sampler2D Bloom_Input;
uniform bool horizontal;

const float weights[3] = float[](0.227027, 0.316216216, 0.07027027);
const float offsets[3] = float[](0.0, 1.3846153846, 3.2307692308);

void main() {
    vec2 tex_offset = 1.0 / textureSize(Bloom_Input, 0); 
    vec3 result = texture(Bloom_Input, v_uv).rgb * weights[0];
    
    if (horizontal) {
        for (int i = 1; i < 3; ++i) {
            result += texture(Bloom_Input, v_uv + vec2(tex_offset.x * offsets[i], 0.0)).rgb * weights[i];
            result += texture(Bloom_Input, v_uv - vec2(tex_offset.x * offsets[i], 0.0)).rgb * weights[i];
        }
    } else {
        for (int i = 1; i < 3; ++i) {
            result += texture(Bloom_Input, v_uv + vec2(0.0, tex_offset.y * offsets[i])).rgb * weights[i];
            result += texture(Bloom_Input, v_uv - vec2(0.0, tex_offset.y * offsets[i])).rgb * weights[i];
        }
    }
    
    BloomBlur_Out = vec4(result, 1.0);
}