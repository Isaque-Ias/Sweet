#version 330 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color;
layout(location = 2) in vec2 a_texcoord;
layout(location = 3) in vec2 iPos;
layout(location = 4) in vec2 iScale;
layout(location = 5) in vec2 iRot;
layout(location = 6) in vec2 iUVOff;
layout(location = 7) in vec2 iUVScale;

uniform mat4 u_mvp;

out vec3 v_color;
out vec2 v_texcoord;

void main()
{
    vec2 pos = a_position.xy * iScale;
    pos = vec2(
        pos.x * iRot.x - pos.y * iRot.y,
        pos.x * iRot.y + pos.y * iRot.x
    );

    pos += iPos;

    gl_Position = u_mvp * vec4(pos, 0.0, 1.0);

    v_color = a_color;

    v_texcoord = a_texcoord * iUVScale + iUVOff;

    v_texcoord.y = v_texcoord.y;
}