#version 460 core

layout(std430, binding = 0) readonly buffer sw_Positions
{
    float positions[];
};

layout(std430, binding = 3) readonly buffer sw_Indices
{
    uint indices[];
};

struct Range
{
    uint offset;
    uint count;
};

struct RenderObject
{
    mat4 model;

    Range positions;
    Range normals;
    Range uvs;
    Range indices;
};

layout(std430, binding = 4) readonly buffer sw_RenderObjects
{
    RenderObject objects[];
};

void main()
{
    RenderObject object = objects[gl_InstanceID];

    uint local_index = uint(gl_VertexID);

    if (local_index >= object.indices.count)
    {
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }

    uint idx_location = object.indices.offset + local_index;
    uint vertex_index = indices[idx_location];
    uint pos_location = object.positions.offset + vertex_index * 3;

    vec3 local_pos = vec3(
        positions[pos_location + 0],
        positions[pos_location + 1],
        positions[pos_location + 2]
    );

    // Transform to world space and pass to geometry shader
    gl_Position = object.model * vec4(local_pos, 1.0);
}