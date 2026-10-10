import math

import sweet as sw
from sweet.resources.assets.generation import ProceduralMesh
from sweet.graphics.upload import UploadManager


def polar_to_cartesian(radius: float, theta: float, phi: float):
    x = radius * math.cos(theta) * math.sin(phi)
    y = radius * math.sin(theta)
    z = radius * math.cos(theta) * math.cos(phi)
    return (x, y, z)


def calculate_sphere_normal(pos):
    """Calculates smooth outward vertex normal for a spherical point."""
    length = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)
    if length < 1e-6:
        return (0.0, 1.0, 0.0)
    return (pos[0] / length, pos[1] / length, pos[2] / length)


# ---------------------------------------------------------------------------
# 1. Smooth UV-Mapped Eyeball Mesh
# ---------------------------------------------------------------------------

def build_eyeball_mesh(
    radius: float = 1.0, 
    lat_segments: int = 32, 
    lon_segments: int = 64
):
    mesh = ProceduralMesh("procedural_eyeball", normals=True, texcoord_0=True)

    # 1. Add unique shared vertices to the pool
    vertex_grid = []
    for i in range(lat_segments + 1):
        row = []
        v_factor = i / lat_segments
        theta = (v_factor - 0.5) * math.pi  # -pi/2 to +pi/2

        for j in range(lon_segments + 1):
            u_factor = j / lon_segments
            phi = (u_factor - 0.5) * 2.0 * math.pi  # -pi to +pi

            pos = polar_to_cartesian(radius, theta, phi)
            uv = (u_factor, v_factor)

            # Add vertex to storage and hold onto its index
            idx = mesh.add_vertex(pos, uv=uv)
            row.append(idx)
        vertex_grid.append(row)

    # 2. Connect the vertices using indexed triangles (enables shared edges)
    for i in range(lat_segments):
        for j in range(lon_segments):
            idx0 = vertex_grid[i][j]
            idx1 = vertex_grid[i + 1][j]
            idx2 = vertex_grid[i + 1][j + 1]
            idx3 = vertex_grid[i][j + 1]

            # Counter-clockwise winding for outward faces
            mesh.add_indexed_triangle(idx0, idx2, idx1)
            mesh.add_indexed_triangle(idx0, idx3, idx2)

    # 3. Compute and blend smooth barycentric normals across all shared vertices
    mesh.generate_normals(smooth=True)

    return mesh.build()


# ---------------------------------------------------------------------------
# Smooth Almond Eyelids (Using Index Buffer & Smooth Normals)
# ---------------------------------------------------------------------------

def build_eyelids_mesh(
    radius: float = 1.03,
    openness: float = 0.6,
    lat_segments: int = 24,
    lon_segments: int = 48
):
    mesh = ProceduralMesh("procedural_eyelids", normals=True, texcoord_0=True)
    max_aperture = math.radians(40) * openness

    def build_lid(start_is_top: bool):
        vertex_grid = []
        for i in range(lat_segments + 1):
            row = []
            t_lat = i / lat_segments

            for j in range(lon_segments + 1):
                u_lon = j / lon_segments
                phi = (u_lon - 0.5) * math.pi

                corner_scale = math.cos(phi)
                aperture_theta = max_aperture * corner_scale

                if start_is_top:
                    theta = (math.pi / 2.0) - t_lat * ((math.pi / 2.0) - aperture_theta)
                else:
                    theta = -aperture_theta - t_lat * ((math.pi / 2.0) - aperture_theta)

                pos = polar_to_cartesian(radius, theta, phi)
                uv = (u_lon, t_lat)

                idx = mesh.add_vertex(pos, uv=uv)
                row.append(idx)
            vertex_grid.append(row)

        for i in range(lat_segments):
            for j in range(lon_segments):
                idx0 = vertex_grid[i][j]
                idx1 = vertex_grid[i + 1][j]
                idx2 = vertex_grid[i + 1][j + 1]
                idx3 = vertex_grid[i][j + 1]

                mesh.add_indexed_triangle(idx2, idx0, idx1)
                mesh.add_indexed_triangle(idx3, idx0, idx2)

    build_lid(start_is_top=True)
    build_lid(start_is_top=False)

    # Blends normals seamlessly across shared mesh vertices
    mesh.generate_normals(smooth=True)

    return mesh.build()

# ---------------------------------------------------------------------------
# Generator Entry Point
# ---------------------------------------------------------------------------

def generate_procedural_eye(
    scene, 
    eye_material, 
    eyelid_material, 
    radius: float = 1.0, 
    openness: float = 0.5
):
    """Builds and adds the eye and eyelids to the engine scene."""
    entities = []

    # 1. Eyeball entity
    eyeball_data = build_eyeball_mesh(radius=radius, lat_segments=32, lon_segments=64)
    eyeball_view = UploadManager.upload_mesh(eyeball_data)
    
    eyeball_ent = sw.Entity("procedural_eyeball")
    eyeball_ent.attach_visual(sw.Visual(eyeball_view[0], eye_material))
    scene.add_entity(eyeball_ent)
    entities.append(eyeball_ent)

    # 2. Eyelids entity
    eyelid_data = build_eyelids_mesh(radius=radius * 1.025, openness=openness)
    eyelid_view = UploadManager.upload_mesh(eyelid_data)

    eyelid_ent = sw.Entity("procedural_eyelids")
    eyelid_ent.attach_visual(sw.Visual(eyelid_view[0], eyelid_material))
    scene.add_entity(eyelid_ent)
    entities.append(eyelid_ent)

    return entities