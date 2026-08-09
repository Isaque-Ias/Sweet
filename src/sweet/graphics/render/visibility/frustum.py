from __future__ import annotations
import numpy as np
from sweet.plataform.hal.manager import GraphicsDevice
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from sweet.gameplay.scene import Scene

class FrustumCulling:
    @classmethod
    def initialize(cls, device: GraphicsDevice):
        cls.gfx_device = device

    @staticmethod
    def _extract_frustum(vp_matrix: bytes) -> np.ndarray:
        m = np.array(vp_matrix, dtype=np.float32).T
        planes = np.zeros((6, 4), dtype=np.float32)
        
        planes[0] = m[3] + m[0] # left
        planes[1] = m[3] - m[0] # right
        planes[2] = m[3] + m[1] # bottom
        planes[3] = m[3] - m[1] # top
        planes[4] = m[3] + m[2] # near
        planes[5] = m[3] - m[2] # far

        lengths = np.sqrt(np.sum(planes[:, 0:3] ** 2, axis=1, keepdims=True))
        
        planes /= lengths
            
        return planes

    @classmethod
    def init_command_buffers(cls, total_entities: int):
        cls.cpu_commands = np.zeros((total_entities, 5), dtype=np.uint32)
        cls.cpu_commands[:, 0] = 36
        cls.cpu_commands[:, 4] = np.arange(total_entities, dtype=np.uint32)

    @classmethod
    def run_culling(cls, scene: Scene, vp_matrix_ptr: Any):
        track = scene.data_track
        total_entities = track.size
        if total_entities == 0:
            return

        cls.cpu_commands[:total_entities, 1] = 1
        return np.arange(total_entities)

        planes = cls._extract_frustum(vp_matrix_ptr)
        normals = planes[:, 0:3]
        d = planes[:, 3:4]
        
        positions = track.transforms[:total_entities, 0:3]
        scales = track.transforms[:total_entities, 7:10]
        local_extents = track.boundings[:total_entities, 0:3]
        world_extents = local_extents * scales

        center_distance = np.dot(normals, positions.T) + d
        effective_radius = np.dot(np.abs(normals), world_extents.T)
        outside = center_distance < -effective_radius
        individual_visibility = ~np.any(outside, axis=0)

        parent_indices = track.parent_ids[:total_entities]
        parent_visibility = individual_visibility[parent_indices]

        final_visibility = parent_visibility & individual_visibility 

        cls.cpu_commands[:total_entities, 1] = np.where(final_visibility, 1, 0)
        # track.gpu_commands.upload_data(cls.cpu_commands[:total_entities].tobytes())
        visible_entity_ids = np.flatnonzero(final_visibility)
        return visible_entity_ids