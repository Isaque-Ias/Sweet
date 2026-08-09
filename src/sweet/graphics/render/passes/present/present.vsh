#version 430 core

out vec2 v_uv;

void main()
{
    vec2 positions[3] = vec2[](
        vec2(-1.0, -1.0),
        vec2( 3.0, -1.0),
        vec2(-1.0,  3.0)
    );

    vec2 pos = positions[gl_VertexID];

    v_uv = pos * 0.5 + 0.5;

    gl_Position = vec4(pos, 0.0, 1.0);
}