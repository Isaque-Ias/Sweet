"""
Chunked procedural terrain with concentric LOD rings.

Design:
  - CORE_CHUNKS x CORE_CHUNKS grid (default 4x4) built at BASE_CELL_SIZE.
  - LOD_LEVELS additional rings around it. Each ring level doubles cell_size
    (so each triangle's edge length doubles), while keeping the same
    CORE_CHUNKS x CORE_CHUNKS grid shape.
  - Because doubling cell_size doubles a level's total physical footprint,
    the central 2x2 chunks of every ring are *exactly* covered by the full
    footprint of the level directly beneath it -> we skip building those,
    so there is never overlapping/duplicate geometry between levels.
  - Height is sampled in WORLD space (not chunk-local space), so triangle
    edges match up seamlessly both between neighboring chunks and between
    LOD levels.

Drop into your script and call:

    material = list(assetsm1[0].materials.values())[0]
    generate_terrain(scene, material)
"""

import math

import sweet as sw
from sweet.resources.assets.generation import ProceduralMesh
from sweet.graphics.upload import UploadManager


# ---------------------------------------------------------------------------
# Perlin / FBM noise (unchanged from your version)
# ---------------------------------------------------------------------------

_PERM = [
    151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225,
    140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 21, 10, 23, 190, 6, 148,
    247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 11, 32,
    57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175,
    74, 165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122,
    60, 211, 133, 230, 220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 143, 54,
    65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208, 89, 18, 169,
    200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3,
    64, 52, 217, 226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85,
    212, 207, 206, 59, 227, 47, 16, 58, 17, 182, 189, 28, 42, 223, 183, 170,
    213, 119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155, 167, 43, 172,
    9, 129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185, 112,
    104, 218, 246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191, 179, 162,
    241, 81, 51, 145, 235, 249, 14, 239, 107, 49, 192, 214, 31, 181, 199, 106,
    157, 184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150, 254, 138, 236, 205,
    93, 222, 114, 67, 29, 24, 72, 243, 141, 128, 195, 78, 66, 215, 61, 156,
]
_P = _PERM * 20


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(t: float, a: float, b: float) -> float:
    return a + t * (b - a)


def _grad(hash_val: int, x: float, y: float) -> float:
    h = hash_val & 7
    u = x if h < 4 else y
    v = y if h < 4 else x
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


def get_perlin_raw(x: float, y: float) -> float:
    X = math.floor(x) & 255
    Y = math.floor(y) & 255

    x_rel = x - math.floor(x)
    y_rel = y - math.floor(y)

    u = _fade(x_rel)
    v = _fade(y_rel)

    A = _P[X] + Y
    B = _P[X + 1] + Y

    g00 = _grad(_P[A], x_rel, y_rel)
    g10 = _grad(_P[B], x_rel - 1, y_rel)
    g01 = _grad(_P[A + 1], x_rel, y_rel - 1)
    g11 = _grad(_P[B + 1], x_rel - 1, y_rel - 1)

    nx0 = _lerp(u, g00, g10)
    nx1 = _lerp(u, g01, g11)
    return _lerp(v, nx0, nx1)


def get_fbm_height(
    i: float,
    j: float,
    octaves: int = 8,
    persistence: float = 0.75,
    lacunarity: float = 2.0,
    base_scale: float = 0.01,
    max_height: float = 30.0,
    exponent: float = 1.5,
) -> float:
    total_noise = 0.0
    amplitude = 1.0
    frequency = base_scale
    max_possible_val = 0.0

    for _ in range(octaves):
        noise_val = get_perlin_raw(j * frequency, i * frequency)
        total_noise += noise_val * amplitude
        max_possible_val += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    normalized = (total_noise / max_possible_val + 1.0) / 2.0
    if exponent != 1.0:
        normalized = math.pow(normalized, exponent)

    return normalized * max_height


def sample_height(world_x: float, world_z: float) -> float:
    """World-space height lookup. Always call with world coords (not
    chunk-local coords) so neighboring chunks / LOD levels line up."""
    return get_fbm_height(i=world_z, j=world_x)


# ---------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------

def calc_normal(p0, p1, p2):
    e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

    nx = e1[1] * e2[2] - e1[2] * e2[1]
    ny = e1[2] * e2[0] - e1[0] * e2[2]
    nz = e1[0] * e2[1] - e1[1] * e2[0]

    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-6:
        return (0.0, 1.0, 0.0)

    return (nx / length, ny / length, nz / length)


def add_quad(mesh, h00, h10, h11, h01, wx, wz, cell_size):
    """Adds one grid cell (two triangles) at world position (wx, wz)."""
    p0 = (wx, h00, wz)
    p1 = (wx + cell_size, h10, wz)
    p2 = (wx + cell_size, h11, wz - cell_size)
    p3 = (wx, h01, wz - cell_size)

    n1 = calc_normal(p0, p1, p2)
    mesh.add_triangle(p0, p1, p2, normal=n1, uv=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)))

    n2 = calc_normal(p0, p2, p3)
    mesh.add_triangle(p0, p2, p3, normal=n2, uv=((0.0, 0.0), (1.0, 1.0), (0.0, 1.0)))


def build_chunk_mesh(chunk_x: int, chunk_z: int, cell_size: float, grid_size: int):
    """
    Builds one terrain chunk.

    chunk_x / chunk_z are chunk-grid coordinates (integers), not world units.
    cell_size is the world-space edge length of one grid cell for this chunk
    (this is what you double per LOD level -> triangles get 2x bigger).
    """
    mesh = ProceduralMesh(
        f"chunk_{chunk_x}_{chunk_z}_{cell_size:g}",
        normals=True,
        texcoord_0=True,
    )

    chunk_world_size = grid_size * cell_size
    origin_x = chunk_x * chunk_world_size
    origin_z = chunk_z * chunk_world_size

    h_map = [
        [
            sample_height(origin_x + j * cell_size, origin_z - i * cell_size)
            for j in range(grid_size + 1)
        ]
        for i in range(grid_size + 1)
    ]

    for i in range(grid_size):
        for j in range(grid_size):
            add_quad(
                mesh,
                h_map[i][j], h_map[i][j + 1],
                h_map[i + 1][j + 1], h_map[i + 1][j],
                origin_x + j * cell_size,
                origin_z - i * cell_size,
                cell_size,
            )

    return mesh.build()


# ---------------------------------------------------------------------------
# LOD ring layout
# ---------------------------------------------------------------------------

CORE_CHUNKS = 4        # chunks per side, per level (4x4)
GRID_SIZE = 40         # vertices per side, per chunk mesh
BASE_CELL_SIZE = 1.0   # world size of one cell at level 0
LOD_LEVELS = 16        # number of doubling rings around the core


def chunk_positions_for_level(level: int, core_chunks: int = CORE_CHUNKS):
    """
    Chunk-grid coordinates to build at a given LOD level.

    Level 0: the full core_chunks x core_chunks grid.
    Level >0: the same grid minus its central 2x2 -- that region is exactly
    covered by the full footprint of level - 1 (since cell_size doubles each
    level, a level's total footprint is 2x the previous level's).
    """
    half = core_chunks // 2
    coords = range(-half, half)

    if level == 0:
        return [(x, z) for x in coords for z in coords]

    skip_lo, skip_hi = -(half // 2), half // 2  # central 2x2 -> (-1, 0)
    skip = range(skip_lo, skip_hi)
    return [
        (x, z) for x in coords for z in coords
        if x not in skip or z not in skip
    ]


def generate_terrain(scene, material, lod_levels: int = LOD_LEVELS):
    """Builds the core 4x4 grid plus `lod_levels` doubling rings around it,
    uploads each chunk and attaches it as an entity in `scene`."""
    entities = []

    for level in range(lod_levels + 1):
        cell_size = BASE_CELL_SIZE * (2 ** level)

        for cx, cz in chunk_positions_for_level(level):
            mdata = build_chunk_mesh(cx, cz, cell_size, GRID_SIZE)
            view = UploadManager.upload_mesh(mdata)

            ent = sw.Entity(f"terrain_L{level}_{cx}_{cz}")
            ent.attach_visual(sw.Visual(view[0], material))
            scene.add_entity(ent)
            entities.append(ent)

    return entities