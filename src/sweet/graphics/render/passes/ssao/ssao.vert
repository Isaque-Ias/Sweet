#version 460 core

out vec2 v_uv;

void main()
{
    /*
     * Fullscreen triangle.
     */
    vec2 positions[3] = vec2[](
        vec2(-1.0, -1.0),
        vec2( 3.0, -1.0),
        vec2(-1.0,  3.0)
    );

    vec2 uvs[3] = vec2[](
        vec2(0.0, 0.0),
        vec2(2.0, 0.0),
        vec2(0.0, 2.0)
    );

    v_uv = uvs[gl_VertexID];

    gl_Position =
        vec4(positions[gl_VertexID], 0.0, 1.0);
}