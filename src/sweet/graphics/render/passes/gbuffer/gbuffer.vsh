#version 460 core

layout(std430, binding = 0) readonly buffer sw_Positions { float positions[]; };
layout(std430, binding = 1) readonly buffer sw_Normals   { float normals[]; };
layout(std430, binding = 2) readonly buffer sw_UVs       { float uvs[]; };
layout(std430, binding = 3) readonly buffer sw_Indices   { uint indices[]; };

struct Range { uint offset; uint count; };
struct RenderObject {
    mat4 model;
    Range positions;
    Range normals;
    Range uvs;
    Range indices;
};

layout(std430, binding = 4) readonly buffer sw_RenderObjects {
    RenderObject objects[];
};

uniform mat4 sw_View;
uniform mat4 sw_Projection;

out vec3 v_world_position;
out vec3 v_world_normal;
out vec2 v_texcoord;
out vec4 v_view_position;

void main()
{
    RenderObject object = objects[gl_InstanceID];
    uint local_index = uint(gl_VertexID);

    if (local_index >= object.indices.count) {
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }

    uint idx_location = object.indices.offset + local_index;
    uint vertex_index = indices[idx_location];

    uint pos_base = object.positions.offset + (vertex_index * 3);
    vec3 local_pos = vec3(positions[pos_base], positions[pos_base + 1], positions[pos_base + 2]);

    uint norm_base = object.normals.offset + (vertex_index * 3);
    vec3 local_norm = vec3(normals[norm_base], normals[norm_base + 1], normals[norm_base + 2]);

    uint uv_base = object.uvs.offset + (vertex_index * 2);
    vec2 local_uv = vec2(uvs[uv_base], uvs[uv_base + 1]);

    vec4 world_pos = object.model * vec4(local_pos, 1.0);
    vec4 view_pos = sw_View * world_pos; // View Space Transformation

    v_world_position = world_pos.xyz;
    v_view_position = view_pos;
    v_world_normal = normalize(mat3(object.model) * local_norm);
    v_texcoord = local_uv;

    gl_Position = sw_Projection * view_pos;
}