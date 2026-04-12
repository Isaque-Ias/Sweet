from sweet.common import PathType, Interpolation, Controls
from sweet.linalg.vector import Vec
from numpy import clip
from math import comb
from typing import Sequence

class Path:
    def __init__(self, path_type: PathType, control_points: Sequence[Controls]) -> None:
        self.path_type = path_type
        self.set_points(control_points)
    
    def set_points(self, points: Sequence[Controls]) -> None:
        self._control_points = points

    @staticmethod
    def remap(t: float, t_min: float, t_max: float, n_min: float, n_max: float) -> float:
        return (t - t_min) / (t_max - t_min) * (n_max - n_min) + n_min

    def get_sector(self, t: float) -> float:
        parts = len(self._control_points) - 1
        index = int(t * parts)
        return index - 1 if index == parts else index

    def path_at(self, t: float) -> Vec:
        if len(self._control_points) <= 1:
            return Vec(0, 0)
        if t >= 1: t = 1
        index = self.get_sector(t)
        total_points = len(self._control_points)
        
        interval_t = self.remap(t, index / (total_points - 1), (index + 1) / (total_points - 1), 0, 1)
        
        if self.path_type == PathType.PIECEWISE:
            controls = [self._control_points[index], self._control_points[index + 1]]
            return controls[0] * (1 - interval_t) + controls[1] * interval_t
        elif self.path_type == PathType.BEZIER:
            controls = [
                self._control_points[index][1],
                self._control_points[index][2],
                self._control_points[index+1][0],
                self._control_points[index+1][1],
            ]
            final_pos = Vec(0, 0)
            for i in range(4):
                final_pos += comb(3, i) * interval_t ** i * (1 - interval_t) ** (3 - i) * controls[i]
            return final_pos

    @staticmethod
    def ease(t: float, method: Interpolation, clamp: bool=True) -> float:
        if clamp:
            t = clip(t, 0, 1)
        if method == Interpolation.QUAD:
            return 2 * t * t if t < 1 / 2 else 1 - 2 * (t - 1) * (t - 1)
        if method == Interpolation.QUAD_IN:
            return t * t
        if method == Interpolation.QUAD_OUT:
            return 1 - (t - 1) * (t - 1)
        return t