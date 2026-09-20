#version 330 core
out vec4 Bloom_Final;
in vec2 v_uv;

uniform sampler2D u_srcTexture;
uniform float u_srcMipLevel;
uniform vec2 u_texelSize;
uniform float u_filterRadius;
uniform int u_mode; // 0 = Downsample, 1 = Upsample

vec3 Downsample13Tap() {
    float x = u_texelSize.x;
    float y = u_texelSize.y;

    vec3 a = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y + 2.0*y), u_srcMipLevel).rgb;
    vec3 b = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y + 2.0*y), u_srcMipLevel).rgb;
    vec3 c = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y + 2.0*y), u_srcMipLevel).rgb;
    vec3 d = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y),        u_srcMipLevel).rgb;
    vec3 e = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y),        u_srcMipLevel).rgb;
    vec3 f = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y),        u_srcMipLevel).rgb;
    vec3 g = textureLod(u_srcTexture, vec2(v_uv.x - 2.0*x, v_uv.y - 2.0*y), u_srcMipLevel).rgb;
    vec3 h = textureLod(u_srcTexture, vec2(v_uv.x,         v_uv.y - 2.0*y), u_srcMipLevel).rgb;
    vec3 i = textureLod(u_srcTexture, vec2(v_uv.x + 2.0*x, v_uv.y - 2.0*y), u_srcMipLevel).rgb;
    vec3 j = textureLod(u_srcTexture, vec2(v_uv.x - x,     v_uv.y + y),     u_srcMipLevel).rgb;
    vec3 k = textureLod(u_srcTexture, vec2(v_uv.x + x,     v_uv.y + y),     u_srcMipLevel).rgb;
    vec3 l = textureLod(u_srcTexture, vec2(v_uv.x - x,     v_uv.y - y),     u_srcMipLevel).rgb;
    vec3 m = textureLod(u_srcTexture, vec2(v_uv.x + x,     v_uv.y - y),     u_srcMipLevel).rgb;

    vec3 color = e * 0.125;
    color += (a + c + g + i) * 0.03125;
    color += (b + d + f + h) * 0.0625;
    color += (j + k + l + m) * 0.125;
    return color;
}

vec3 UpsampleTent9Tap() {
    float x = u_filterRadius * u_texelSize.x;
    float y = u_filterRadius * u_texelSize.y;

    vec3 a = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y + y), u_srcMipLevel).rgb;
    vec3 b = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y + y), u_srcMipLevel).rgb;
    vec3 c = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y + y), u_srcMipLevel).rgb;
    vec3 d = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y),    u_srcMipLevel).rgb;
    vec3 e = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y),    u_srcMipLevel).rgb;
    vec3 f = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y),    u_srcMipLevel).rgb;
    vec3 g = textureLod(u_srcTexture, vec2(v_uv.x - x, v_uv.y - y), u_srcMipLevel).rgb;
    vec3 h = textureLod(u_srcTexture, vec2(v_uv.x,     v_uv.y - y), u_srcMipLevel).rgb;
    vec3 i = textureLod(u_srcTexture, vec2(v_uv.x + x, v_uv.y - y), u_srcMipLevel).rgb;

    vec3 color = e * 4.0;
    color += (b + d + f + h) * 2.0;
    color += (a + c + g + i);
    return color * (1.0 / 16.0);
}

void main() {
    if (u_mode == 0) {
        Bloom_Final = vec4(Downsample13Tap(), 1.0);
    } else {
        Bloom_Final = vec4(UpsampleTent9Tap(), 1.0);
    }
}