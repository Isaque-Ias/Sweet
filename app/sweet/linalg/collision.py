from OpenGL.GL import *
from pygame.locals import *
from .vector import Vec
from typing import Sequence

class Mask:
    def __init__(self, vertices: Sequence[Vec]) -> None:
        self.vertices = vertices

class Collision:
    @staticmethod
    def collision_data(x1: Mask, x2: Mask) -> dict | bool:
        lowest_overlap: float = float("inf")
        overlap_axis: Vec = Vec(0, 0)
        is_b: bool = False

        contact_point: bool = Vec(0, 0)

        for shape in (x1, x2):
            verts = shape.vertices
            for i in range(len(verts)):
                v1: Vec = verts[i]
                v2: Vec = verts[(i + 1) % len(verts)]

                axis: Vec = (v2 - v1).rotate90().normalize()

                min_a: float = float("inf")
                max_a: float = float("-inf")
                for v in x1.vertices:
                    p: float = axis.dot(v)
                    min_a: float = min(min_a, p)
                    max_a: float = max(max_a, p)

                min_b: float = float("inf")
                max_b: float = float("-inf")
                for v in x2.vertices:
                    p: float = axis.dot(v)
                    min_b: float = min(min_b, p)
                    max_b: float = max(max_b, p)

                if max_a <= min_b or max_b <= min_a:
                    return False

                overlap: float = min(max_a, max_b) - max(min_a, min_b)
        
                if overlap < lowest_overlap:
                    lowest_overlap: float = overlap
                    
                    direction: Vec = (x2.pos - x1.pos)
                    if axis.dot(direction) < 0:
                        axis: Vec = -axis

                    overlap_axis: Vec = axis

        return {'mtv': overlap_axis * lowest_overlap, "normal": overlap_axis, "is_b": is_b, "contact_point": contact_point}

    @classmethod
    def get_collisions(cls, object) -> None:
        for x in range(-1, 2):
            for y in range(-1, 2):
                key = cls.to_key((Vec(*object.mesh_coordinate) + (x, y)).unp())
                mesh_grid = cls.mesh.get(key)
                if mesh_grid == None: continue

                for obj_key in mesh_grid:
                    if obj_key == object.uid: continue

                    if cls.collision_manifold.get(f'{object.uid};{obj_key}'): continue

                    cls.collision_manifold[f'{obj_key};{object.uid}'] = cls.collision_data(object, mesh_grid[obj_key])

    @classmethod
    def get_contact_points(cls, x1, x2, normal):
        ref_i = cls.find_reference_edge(x1.vertices, normal)
        inc_i = cls.find_incident_edge(x2.vertices, normal)

        ref_v1 = x1.vertices[ref_i]
        ref_v2 = x1.vertices[(ref_i+1) % len(x1.vertices)]

        inc_v1 = x2.vertices[inc_i]
        inc_v2 = x2.vertices[(inc_i+1) % len(x2.vertices)]

        ref_edge = (ref_v2 - ref_v1).normalize()
        ref_normal = ref_edge.rotate90()

        offset = ref_normal.dot(ref_v1)

        clipped = cls.clip(inc_v1, inc_v2,  ref_normal, offset)
        if len(clipped) < 2:
            return []

        clipped = cls.clip(clipped[0], clipped[1], -ref_normal, -ref_normal.dot(ref_v2))

        return clipped

    @staticmethod
    def find_reference_edge(vertices, normal):
        best = -float("inf")
        index = 0
        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i+1) % len(vertices)]
            edge = (v2 - v1).normalize()
            face_normal = edge.rotate90()
            d = face_normal.dot(normal)
            if d > best:
                best = d
                index = i
        return index

    @staticmethod
    def clip(v1, v2, normal, offset):
        out = []

        d1 = normal.dot(v1) - offset
        d2 = normal.dot(v2) - offset

        if d1 <= 0:
            out.append(v1)
        if d2 <= 0:
            out.append(v2)

        if d1 * d2 < 0:
            t = d1 / (d1 - d2)
            out.append(v1 + (v2 - v1) * t)

        return out