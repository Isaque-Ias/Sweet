import moderngl
import numpy as np

ctx = moderngl.create_standalone_context()
W, H = 512, 512

# 1. Shader setup with a Geometry Shader that uses gl_Layer
prog = ctx.program(
    vertex_shader="""
        #version 460 core
        in vec3 in_position;
        void main() {
            gl_Position = vec4(in_position, 1.0);
        }
    """,
    geometry_shader="""
        #version 460 core
        layout(triangles) in;
        layout(triangle_strip, max_vertices = 18) out;

        // Renders a triangle to all 6 faces of a cubemap (or 4 layers of an array)
        void main() {
            for (int layer = 0; layer < 6; ++layer) {
                gl_Layer = layer; // <--- The magic line for single-pass layered rendering
                for (int i = 0; i < 3; ++i) {
                    // Apply face-specific view/projection matrices here if needed
                    gl_Position = gl_in[i].gl_Position;
                    EmitVertex();
                }
                EndPrimitive();
            }
        }
    """,
    fragment_shader="""
        #version 460 core
        out vec4 f_color;
        void main() {
            f_color = vec4(0.2, 0.6, 1.0, 1.0);
        }
    """,
)

# Dummy triangle geometry
vertices = np.array([0.0, 0.8, 0.0, -0.8, -0.8, 0.0, 0.8, -0.8, 0.0], dtype="f4")
vbo = ctx.buffer(vertices)
vao = ctx.vertex_array(prog, [(vbo, "3f", "in_position")])

# ==========================================
# EXAMPLE A: Single-Pass Cubemap Rendering
# ==========================================
# Create a full TextureCube (automatically has 6 faces)
cubemap = ctx.texture_cube((W, H), 4)

# Attach the ENTIRE cubemap to the framebuffer (not .layer())
cube_fbo = ctx.framebuffer(color_attachments=[
        cubemap.layer(0),
        cubemap.layer(1),
        cubemap.layer(2),
        cubemap.layer(3),
        cubemap.layer(4),
        cubemap.layer(5),
    ]
)

cube_fbo.use()
ctx.clear(0.0, 0.0, 0.0, 1.0)
vao.render()  # Renders to all 6 faces at once via the Geometry Shader!


# ==========================================
# EXAMPLE B: Single-Pass Texture Array Rendering
# ==========================================
layers = 4
texture_array = ctx.texture_array((W, H, layers), 4)

# Attach the ENTIRE texture array to the framebuffer
array_fbo = ctx.framebuffer(color_attachments=[texture_array])

array_fbo.use()
ctx.clear(0.0, 0.0, 0.0, 1.0)
# (If using a geometry shader set up for 4 layers instead of 6, it populates all 4 slices)
vao.render() 

print("Single-pass layered rendering complete!")