#version 460 core

uniform mat4 sw_InvProjection;
uniform mat4 sw_InvView;

out vec2 v_uv;
out vec3 v_dir;

void main()
{
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

    vec2 position = positions[gl_VertexID];
    v_uv = uvs[gl_VertexID];

    // 1. Unproject screen quad position into view-space ray
    vec4 view_ray = sw_InvProjection * vec4(position, 1.0, 1.0);

    // 2. Extract rotation-only (mat3) from Inverse View matrix to strip translation
    mat3 invViewRot = mat3(sw_InvView);

    // 3. Transform ray into world space using pure rotation
    v_dir = invViewRot * view_ray.xyz;

    gl_Position = vec4(position, 0.0, 1.0);
}