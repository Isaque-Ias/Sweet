#version 330 core
out vec4 Bloom_Final;
in vec2 v_uv;

uniform sampler2D u_srcTexture;
uniform float u_srcMipLevel;
uniform vec2 u_texelSize;      // 1.0 / destination_resolution
uniform float u_filterRadius;  // Set to 1.0 - 2.0 (scales in texel-space)

void main() {
    // Texel-space offset calculation guarantees exponential physical scaling
    float x = u_filterRadius * u_texelSize.x;
    float y = u_filterRadius * u_texelSize.y;

    // 9-tap tent filter
    vec3 a = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y + y), u_srcMipLevel).rgb;
    vec3 b = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y + y), u_srcMipLevel).rgb;
    vec3 c = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y + y), u_srcMipLevel).rgb;

    vec3 d = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y),    u_srcMipLevel).rgb;
    vec3 e = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y),    u_srcMipLevel).rgb;
    vec3 f = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y),    u_srcMipLevel).rgb;

    vec3 g = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y - y), u_srcMipLevel).rgb;
    vec3 h = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y - y), u_srcMipLevel).rgb;
    vec3 i = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y - y), u_srcMipLevel).rgb;

    vec3 upsample = e * 4.0;
    upsample += (b + d + f + h) * 2.0;
    upsample += (a + c + g + i);
    upsample *= (1.0 / 16.0);

    Bloom_Final = vec4(upsample, 1.0);
}