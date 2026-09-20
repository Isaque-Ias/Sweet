#version 330 core
out vec4 Bloom_Downsampled;
in vec2 v_uv;

uniform sampler2D u_srcTexture;
uniform float u_srcMipLevel; // Mip level to read from
uniform vec2 u_texelSize;   // 1.0 / source_resolution

void main() {
    float x = u_texelSize.x;
    float y = u_texelSize.y;

    // 13-tap cross sample around v_uv using textureLod
    vec3 a = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y + 2.0*y), u_srcMipLevel).rgb;
    vec3 b = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y + 2.0*y), u_srcMipLevel).rgb;
    vec3 c = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y + 2.0*y), u_srcMipLevel).rgb;

    vec3 d = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y),        u_srcMipLevel).rgb;
    vec3 e = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y),        u_srcMipLevel).rgb;
    vec3 f = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y),        u_srcMipLevel).rgb;

    vec3 g = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y - 2.0*y), u_srcMipLevel).rgb;
    vec3 h = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y - 2.0*y), u_srcMipLevel).rgb;
    vec3 i = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y - 2.0*y), u_srcMipLevel).rgb;

    vec3 j = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y + y), u_srcMipLevel).rgb;
    vec3 k = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y + y), u_srcMipLevel).rgb;
    vec3 l = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y - y), u_srcMipLevel).rgb;
    vec3 m = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y - y), u_srcMipLevel).rgb;

    vec3 downsample = e * 0.125;
    downsample += (a + c + g + i) * 0.03125;
    downsample += (b + d + f + h) * 0.0625;
    downsample += (j + k + l + m) * 0.125;

    Bloom_Downsampled = vec4(max(downsample, vec3(0.0)), 1.0);
}