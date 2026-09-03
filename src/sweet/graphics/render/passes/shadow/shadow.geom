#version 460 core

layout(triangles) in;
// 3 vertices per triangle * up to 4 cascades = 12 max vertices (16 is safe)
layout(triangle_strip, max_vertices = 16) out;

const int MAX_CASCADES = 4;

uniform int sw_CascadeCount;
uniform mat4 sw_LightViewProjections[MAX_CASCADES];

void main()
{
    // Loop through each cascade layer
    for (int c = 0; c < sw_CascadeCount; ++c)
    {
        // Select which layer of the texture2darray to render into
        gl_Layer = c;

        for (int i = 0; i < 3; ++i)
        {
            // gl_in[i].gl_Position is the world_pos from the vertex shader
            gl_Position = sw_LightViewProjections[c] * gl_in[i].gl_Position;
            EmitVertex();
        }
        EndPrimitive();
    }
}