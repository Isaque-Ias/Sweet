#version 460 core

in vec2 v_uv;

layout(location = 0) out vec4 out_color;

uniform sampler2D sw_Lighting;

void main()
{
    vec3 color =
        texture(
            sw_Lighting,
            v_uv
        ).rgb;

    /*
     * Temporary display transform.
     *
     * The lighting buffer can later be HDR.
     */
    color =
        color / (color + vec3(1.0));

    /*
     * Gamma correction.
     */
    color =
        pow(
            color,
            vec3(1.0 / 2.2)
        );

    out_color =
        vec4(color, 1.0);
}