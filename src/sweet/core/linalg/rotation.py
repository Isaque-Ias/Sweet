from enum import Enum, auto
from .vector import Vec, Vec3, VectorLike
from typing import Tuple, List
import math

class RotationModel(Enum):
    EULER_XYZ = auto()
    EULER_ZYX = auto()
    QUATERNION = auto()
    VECTOR = auto()

class Rotation:
    def __init__(self, values: VectorLike = Vec3(), model: RotationModel = RotationModel.VECTOR):
            
        self.model = model
        if isinstance(values, Vec):
            values = values.unp()

        self.values = values

    def convert(self, target_model: RotationModel) -> "Rotation":
        if self.model == target_model:
            return Rotation(self.values, target_model)

        quat = self._to_quaternion()

        new_values = self._from_quaternion(quat, target_model)
        
        return Rotation(new_values, target_model)

    def _to_quaternion(self) -> Tuple[float, float, float, float]:
        vals = self.values

        if self.model == RotationModel.QUATERNION:
            w, x, y, z = vals[0], vals[1], vals[2], vals[3]
            norm = math.sqrt(w*w + x*x + y*y + z*z)
            return (w / norm, x / norm, y / norm, z / norm) if norm > 0 else (1.0, 0.0, 0.0, 0.0)

        elif self.model == RotationModel.EULER_XYZ:
            rx, ry, rz = vals[0] * 0.5, vals[1] * 0.5, vals[2] * 0.5
            cx, sx = math.cos(rx), math.sin(rx)
            cy, sy = math.cos(ry), math.sin(ry)
            cz, sz = math.cos(rz), math.sin(rz)

            w = cx * cy * cz + sx * sy * sz
            x = sx * cy * cz - cx * sy * sz
            y = cx * sy * cz + sx * cy * sz
            z = cx * cy * sz - sx * sy * cz
            return (w, x, y, z)

        elif self.model == RotationModel.EULER_ZYX:
            rz, ry, rx = vals[0] * 0.5, vals[1] * 0.5, vals[2] * 0.5
            cz, sz = math.cos(rz), math.sin(rz)
            cy, sy = math.cos(ry), math.sin(ry)
            cx, sx = math.cos(rx), math.sin(rx)

            w = cz * cy * cx + sz * sy * sx
            x = cz * cy * sx - sz * sy * cx
            y = cz * sy * cx + sz * cy * sx
            z = sz * cy * cx - cz * sy * sx
            return (w, x, y, z)

        elif self.model == RotationModel.VECTOR:
            vx, vy, vz = vals[0], vals[1], vals[2]
            angle = math.sqrt(vx*vx + vy*vy + vz*vz)
            if angle < 1e-8:
                return (1.0, 0.0, 0.0, 0.0)
            
            half_angle = angle * 0.5
            sin_h = math.sin(half_angle)
            return (
                math.cos(half_angle),
                (vx / angle) * sin_h,
                (vy / angle) * sin_h,
                (vz / angle) * sin_h
            )

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")

    def _from_quaternion(self, quat: Tuple[float, float, float, float], target_model: RotationModel) -> List[float]:
        w, x, y, z = quat

        if target_model == RotationModel.QUATERNION:
            return [w, x, y, z]

        elif target_model == RotationModel.EULER_XYZ:
            sinr_cosp = 2 * (w * x + y * z)
            cosr_cosp = 1 - 2 * (x * x + y * y)
            rx = math.atan2(sinr_cosp, cosr_cosp)

            sinp = 2 * (w * y - z * x)
            if abs(sinp) >= 1:
                ry = math.copysign(math.pi / 2, sinp)
            else:
                ry = math.asin(sinp)

            siny_cosp = 2 * (w * z + x * y)
            cosy_cosp = 1 - 2 * (y * y + z * z)
            rz = math.atan2(siny_cosp, cosy_cosp)

            return [rx, ry, rz]

        elif target_model == RotationModel.EULER_ZYX:
            siny_cosp = 2 * (w * z + x * y)
            cosy_cosp = 1 - 2 * (y * y + z * z)
            rz = math.atan2(siny_cosp, cosy_cosp)

            sinp = 2 * (w * y - z * x)
            if abs(sinp) >= 1:
                ry = math.copysign(math.pi / 2, sinp)
            else:
                ry = math.asin(sinp)

            sinr_cosp = 2 * (w * x + y * z)
            cosr_cosp = 1 - 2 * (x * x + y * y)
            rx = math.atan2(sinr_cosp, cosr_cosp)

            return [rz, ry, rx]

        elif target_model == RotationModel.VECTOR:
            angle = 2 * math.acos(max(-1.0, min(1.0, w)))
            sin_half = math.sqrt(max(0.0, 1.0 - w * w))

            if sin_half < 1e-8:
                return [0.0, 0.0, 0.0]

            scale = angle / sin_half
            return [x * scale, y * scale, z * scale]

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")