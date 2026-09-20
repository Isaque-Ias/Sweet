from __future__ import annotations

from typing import Optional, Sequence
import math

import numpy as np

from .import_data import MeshData, PrimitiveData, BufferData


class ProceduralMesh:
    """
    CPU-side procedural mesh builder.

    Produces MeshData compatible with the engine's BufferData format.

    Supported attributes:
        POSITION   -> VEC3 / FLOAT
        NORMAL     -> VEC3 / FLOAT
        TANGENT    -> VEC4 / FLOAT
        TEXCOORD_0 -> VEC2 / FLOAT
        TEXCOORD_1 -> VEC2 / FLOAT
        COLOR_0    -> VEC4 / FLOAT
        JOINTS_0   -> VEC4 / UNSIGNED_INT
        WEIGHTS_0  -> VEC4 / FLOAT

    Indices:
        SCALAR / UNSIGNED_INT
    """

    TRIANGLES = 4

    # Same semantic names used by the glTF importer.
    FLOAT = "FLOAT"
    UNSIGNED_INT = "UNSIGNED_INT"

    def __init__(
        self,
        name: str = "ProceduralMesh",
        *,
        normals: bool = False,
        tangents: bool = False,
        texcoord_0: bool = False,
        texcoord_1: bool = False,
        colors: bool = False,
        joints: bool = False,
        weights: bool = False,
    ):
        self.name = name

        self.use_normals = normals
        self.use_tangents = tangents
        self.use_texcoord_0 = texcoord_0
        self.use_texcoord_1 = texcoord_1
        self.use_colors = colors
        self.use_joints = joints
        self.use_weights = weights

        # Raw CPU data.
        #
        # Keeping these as Python lists makes procedural construction
        # inexpensive. They are converted to numpy arrays during build().
        self.positions: list[float] = []
        self.normals: list[float] = []
        self.tangents: list[float] = []
        self.texcoord_0: list[float] = []
        self.texcoord_1: list[float] = []
        self.colors: list[float] = []
        self.joints: list[int] = []
        self.weights: list[float] = []

        self.indices: list[int] = []

        self.vertex_count = 0

        self._min = [math.inf, math.inf, math.inf]
        self._max = [-math.inf, -math.inf, -math.inf]

    # ================================================================
    # Validation
    # ================================================================

    @staticmethod
    def _vec2(value: Sequence[float]) -> tuple[float, float]:
        if len(value) != 2:
            raise ValueError("Expected a VEC2 value.")

        return (
            float(value[0]),
            float(value[1]),
        )

    @staticmethod
    def _vec3(value: Sequence[float]) -> tuple[float, float, float]:
        if len(value) != 3:
            raise ValueError("Expected a VEC3 value.")

        return (
            float(value[0]),
            float(value[1]),
            float(value[2]),
        )

    @staticmethod
    def _vec4(
        value: Sequence[float],
    ) -> tuple[float, float, float, float]:
        if len(value) != 4:
            raise ValueError("Expected a VEC4 value.")

        return (
            float(value[0]),
            float(value[1]),
            float(value[2]),
            float(value[3]),
        )

    @staticmethod
    def _ivec4(
        value: Sequence[int],
    ) -> tuple[int, int, int, int]:
        if len(value) != 4:
            raise ValueError("Expected 4 joint indices.")

        return (
            int(value[0]),
            int(value[1]),
            int(value[2]),
            int(value[3]),
        )

    # ================================================================
    # Bounds
    # ================================================================

    def _update_bounds(
        self,
        position: Sequence[float],
    ) -> None:
        x, y, z = position

        self._min[0] = min(self._min[0], x)
        self._min[1] = min(self._min[1], y)
        self._min[2] = min(self._min[2], z)

        self._max[0] = max(self._max[0], x)
        self._max[1] = max(self._max[1], y)
        self._max[2] = max(self._max[2], z)

    @property
    def aabb(self) -> list[float]:
        """
        [min_x, min_y, min_z, max_x, max_y, max_z]
        """

        if self.vertex_count == 0:
            return [
                0.0, 0.0, 0.0,
                0.0, 0.0, 0.0,
            ]

        return [
            self._min[0],
            self._min[1],
            self._min[2],
            self._max[0],
            self._max[1],
            self._max[2],
        ]

    def _recalculate_bounds(self) -> None:
        self._min = [math.inf, math.inf, math.inf]
        self._max = [-math.inf, -math.inf, -math.inf]

        for i in range(0, len(self.positions), 3):
            self._update_bounds(
                (
                    self.positions[i],
                    self.positions[i + 1],
                    self.positions[i + 2],
                )
            )

    # ================================================================
    # Vertex
    # ================================================================

    def add_vertex(
        self,
        position: Sequence[float],
        *,
        normal: Optional[Sequence[float]] = None,
        tangent: Optional[Sequence[float]] = None,
        uv: Optional[Sequence[float]] = None,
        uv1: Optional[Sequence[float]] = None,
        color: Optional[Sequence[float]] = None,
        joints: Optional[Sequence[int]] = None,
        weights: Optional[Sequence[float]] = None,
    ) -> int:
        """
        Add one vertex.

        Returns the vertex index.

        Attributes are only stored when their corresponding feature
        was enabled in the constructor.
        """

        position = self._vec3(position)

        self.positions.extend(position)
        self._update_bounds(position)

        # ------------------------------------------------------------
        # Normal
        # ------------------------------------------------------------

        if self.use_normals:
            if normal is None:
                normal = (0.0, 0.0, 0.0)

            self.normals.extend(
                self._vec3(normal)
            )

        # ------------------------------------------------------------
        # Tangent
        # ------------------------------------------------------------

        if self.use_tangents:
            if tangent is None:
                tangent = (1.0, 0.0, 0.0, 1.0)

            self.tangents.extend(
                self._vec4(tangent)
            )

        # ------------------------------------------------------------
        # UV 0
        # ------------------------------------------------------------

        if self.use_texcoord_0:
            if uv is None:
                uv = (0.0, 0.0)

            self.texcoord_0.extend(
                self._vec2(uv)
            )

        # ------------------------------------------------------------
        # UV 1
        # ------------------------------------------------------------

        if self.use_texcoord_1:
            if uv1 is None:
                uv1 = (0.0, 0.0)

            self.texcoord_1.extend(
                self._vec2(uv1)
            )

        # ------------------------------------------------------------
        # Color
        # ------------------------------------------------------------

        if self.use_colors:
            if color is None:
                color = (1.0, 1.0, 1.0, 1.0)

            self.colors.extend(
                self._vec4(color)
            )

        # ------------------------------------------------------------
        # Joints
        # ------------------------------------------------------------

        if self.use_joints:
            if joints is None:
                joints = (0, 0, 0, 0)

            self.joints.extend(
                self._ivec4(joints)
            )

        # ------------------------------------------------------------
        # Weights
        # ------------------------------------------------------------

        if self.use_weights:
            if weights is None:
                weights = (0.0, 0.0, 0.0, 0.0)

            self.weights.extend(
                self._vec4(weights)
            )

        index = self.vertex_count
        self.vertex_count += 1

        return index

    # ================================================================
    # Triangle
    # ================================================================

    def add_triangle(
        self,
        a: Sequence[float],
        b: Sequence[float],
        c: Sequence[float],
        *,
        normal: Optional[Sequence[float]] = None,
        normals: Optional[
            tuple[
                Sequence[float],
                Sequence[float],
                Sequence[float],
            ]
        ] = None,
        uv: Optional[
            tuple[
                Sequence[float],
                Sequence[float],
                Sequence[float],
            ]
        ] = None,
        color: Optional[
            tuple[
                Sequence[float],
                Sequence[float],
                Sequence[float],
            ]
        ] = None,
    ) -> tuple[int, int, int]:
        """
        Add an independent triangle.

        Three vertices are created.

        This is useful for geometry where each triangle may have
        independent normals/UVs/etc.
        """

        if normals is None:
            na = nb = nc = normal
        else:
            na, nb, nc = normals

        if uv is None:
            uva = uvb = uvc = None
        else:
            uva, uvb, uvc = uv

        if color is None:
            ca = cb = cc = None
        else:
            ca, cb, cc = color

        ia = self.add_vertex(
            a,
            normal=na,
            uv=uva,
            color=ca,
        )

        ib = self.add_vertex(
            b,
            normal=nb,
            uv=uvb,
            color=cb,
        )

        ic = self.add_vertex(
            c,
            normal=nc,
            uv=uvc,
            color=cc,
        )

        self.indices.extend(
            (ia, ib, ic)
        )

        return ia, ib, ic

    # ================================================================
    # Indexed triangle
    # ================================================================

    def add_indexed_triangle(
        self,
        a: int,
        b: int,
        c: int,
    ) -> None:
        """
        Add a triangle using already-existing vertices.
        """

        if not 0 <= a < self.vertex_count:
            raise IndexError(f"Invalid vertex index: {a}")

        if not 0 <= b < self.vertex_count:
            raise IndexError(f"Invalid vertex index: {b}")

        if not 0 <= c < self.vertex_count:
            raise IndexError(f"Invalid vertex index: {c}")

        self.indices.extend(
            (a, b, c)
        )

    # ================================================================
    # Quad
    # ================================================================

    def add_quad(
        self,
        a: Sequence[float],
        b: Sequence[float],
        c: Sequence[float],
        d: Sequence[float],
        *,
        normal: Optional[Sequence[float]] = None,
        uv: Optional[
            tuple[
                Sequence[float],
                Sequence[float],
                Sequence[float],
                Sequence[float],
            ]
        ] = None,
    ) -> None:
        """
        Add a quad as two triangles.

             a -------- b
             |        / |
             |      /   |
             |    /     |
             |  /       |
             d -------- c

        Winding:

            a -> b -> c
            a -> c -> d
        """

        if uv is None:
            uva = uvb = uvc = uvd = None
        else:
            uva, uvb, uvc, uvd = uv

        self.add_triangle(
            a,
            b,
            c,
            normal=normal,
            uv=(
                uva,
                uvb,
                uvc,
            ) if uv is not None else None,
        )

        self.add_triangle(
            a,
            c,
            d,
            normal=normal,
            uv=(
                uva,
                uvc,
                uvd,
            ) if uv is not None else None,
        )

    # ================================================================
    # Normal generation
    # ================================================================

    def generate_normals(
        self,
        smooth: bool = True,
    ) -> None:
        """
        Generate vertex normals from the current geometry.

        smooth=True:
            average adjacent triangle normals.

        smooth=False:
            use face normals.

        For smooth normals, vertices must be shared through the index
        buffer for the surfaces to actually connect.
        """

        if self.vertex_count == 0:
            return

        if len(self.indices) % 3 != 0:
            raise ValueError(
                "Triangle index buffer must contain multiples of 3."
            )

        positions = np.asarray(
            self.positions,
            dtype=np.float32,
        ).reshape(
            self.vertex_count,
            3,
        )

        indices = np.asarray(
            self.indices,
            dtype=np.uint32,
        ).reshape(-1, 3)

        generated = np.zeros(
            (self.vertex_count, 3),
            dtype=np.float32,
        )

        for i0, i1, i2 in indices:
            p0 = positions[i0]
            p1 = positions[i1]
            p2 = positions[i2]

            edge1 = p1 - p0
            edge2 = p2 - p0

            normal = np.cross(
                edge1,
                edge2,
            )

            length = np.linalg.norm(normal)

            if length < 1e-12:
                continue

            normal /= length

            if smooth:
                generated[i0] += normal
                generated[i1] += normal
                generated[i2] += normal
            else:
                generated[i0] = normal
                generated[i1] = normal
                generated[i2] = normal

        lengths = np.linalg.norm(
            generated,
            axis=1,
        )

        valid = lengths > 1e-12

        generated[valid] /= lengths[
            valid,
            None,
        ]

        generated[~valid] = (
            0.0,
            1.0,
            0.0,
        )

        self.normals = generated.flatten().tolist()
        self.use_normals = True

    # ================================================================
    # Transformations
    # ================================================================

    def translate(
        self,
        offset: Sequence[float],
    ) -> ProceduralMesh:

        ox, oy, oz = self._vec3(offset)

        for i in range(0, len(self.positions), 3):
            self.positions[i] += ox
            self.positions[i + 1] += oy
            self.positions[i + 2] += oz

        self._recalculate_bounds()

        return self

    def scale(
        self,
        scale: Sequence[float] | float,
    ) -> ProceduralMesh:

        if isinstance(scale, (int, float)):
            sx = sy = sz = float(scale)
        else:
            sx, sy, sz = self._vec3(scale)

        for i in range(0, len(self.positions), 3):
            self.positions[i] *= sx
            self.positions[i + 1] *= sy
            self.positions[i + 2] *= sz

        self._recalculate_bounds()

        return self

    def reverse_winding(self) -> ProceduralMesh:
        """
        Reverse triangle winding and invert normals.
        """

        for i in range(0, len(self.indices), 3):
            self.indices[i + 1], self.indices[i + 2] = (
                self.indices[i + 2],
                self.indices[i + 1],
            )

        if self.use_normals:
            for i in range(0, len(self.normals), 3):
                self.normals[i] *= -1.0
                self.normals[i + 1] *= -1.0
                self.normals[i + 2] *= -1.0

        return self

    # ================================================================
    # BufferData creation
    # ================================================================

    @staticmethod
    def _buffer(
        dim_type: str,
        data_type: str,
        count: int,
        data: Sequence,
        dtype: np.dtype,
    ) -> BufferData:

        array = np.asarray(
            data,
            dtype=dtype,
        )

        return BufferData(
            dim_type=dim_type,
            data_type=data_type,
            count=count,
            data=array,
        )

    def _build_positions(self) -> BufferData:
        return self._buffer(
            "VEC3",
            "FLOAT",
            self.vertex_count,
            self.positions,
            np.dtype(np.float32),
        )

    def _build_normals(self) -> Optional[BufferData]:
        if not self.use_normals:
            return None

        return self._buffer(
            "VEC3",
            "FLOAT",
            self.vertex_count,
            self.normals,
            np.dtype(np.float32),
        )

    def _build_tangents(self) -> Optional[BufferData]:
        if not self.use_tangents:
            return None

        return self._buffer(
            "VEC4",
            "FLOAT",
            self.vertex_count,
            self.tangents,
            np.dtype(np.float32),
        )

    def _build_texcoord_0(self) -> Optional[BufferData]:
        if not self.use_texcoord_0:
            return None

        return self._buffer(
            "VEC2",
            "FLOAT",
            self.vertex_count,
            self.texcoord_0,
            np.dtype(np.float32),
        )

    def _build_texcoord_1(self) -> Optional[BufferData]:
        if not self.use_texcoord_1:
            return None

        return self._buffer(
            "VEC2",
            "FLOAT",
            self.vertex_count,
            self.texcoord_1,
            np.dtype(np.float32),
        )

    def _build_colors(self) -> Optional[BufferData]:
        if not self.use_colors:
            return None

        return self._buffer(
            "VEC4",
            "FLOAT",
            self.vertex_count,
            self.colors,
            np.dtype(np.float32),
        )

    def _build_joints(self) -> Optional[BufferData]:
        if not self.use_joints:
            return None

        return self._buffer(
            "VEC4",
            "UNSIGNED_INT",
            self.vertex_count,
            self.joints,
            np.dtype(np.uint32),
        )

    def _build_weights(self) -> Optional[BufferData]:
        if not self.use_weights:
            return None

        return self._buffer(
            "VEC4",
            "FLOAT",
            self.vertex_count,
            self.weights,
            np.dtype(np.float32),
        )

    def _build_indices(self) -> BufferData:
        return self._buffer(
            "SCALAR",
            "UNSIGNED_INT",
            len(self.indices),
            self.indices,
            np.dtype(np.uint32),
        )

    # ================================================================
    # Build
    # ================================================================

    def build_primitive(
        self,
        *,
        material: Optional[int] = None,
    ) -> PrimitiveData:

        if self.vertex_count == 0:
            raise ValueError(
                "Cannot build an empty procedural mesh."
            )

        if len(self.indices) == 0:
            raise ValueError(
                "Cannot build a mesh without indices."
            )

        if len(self.indices) % 3 != 0:
            raise ValueError(
                "Triangle index buffer must contain multiples of 3."
            )

        return PrimitiveData(
            positions=self._build_positions(),
            normals=self._build_normals(),
            tangents=self._build_tangents(),
            texcoord_0=self._build_texcoord_0(),
            texcoord_1=self._build_texcoord_1(),
            colors=self._build_colors(),
            joints=self._build_joints(),
            weights=self._build_weights(),
            indices=self._build_indices(),

            mode=self.TRIANGLES,
            material=material,
            aabb=self.aabb,
        )

    def build(
        self,
        *,
        material: Optional[int] = None,
    ) -> MeshData:

        primitive = self.build_primitive(
            material=material,
        )

        return MeshData(
            primitives=[primitive],
            aabb=self.aabb,
            name=self.name,
        )

    # ================================================================
    # Clear
    # ================================================================

    def clear(self) -> ProceduralMesh:
        self.positions.clear()
        self.normals.clear()
        self.tangents.clear()
        self.texcoord_0.clear()
        self.texcoord_1.clear()
        self.colors.clear()
        self.joints.clear()
        self.weights.clear()
        self.indices.clear()

        self.vertex_count = 0

        self._min = [
            math.inf,
            math.inf,
            math.inf,
        ]

        self._max = [
            -math.inf,
            -math.inf,
            -math.inf,
        ]

        return self

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3