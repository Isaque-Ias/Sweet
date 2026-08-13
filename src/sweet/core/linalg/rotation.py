from enum import Enum, auto
from .vector import Vec3, Vec4
from typing import Any, overload, Sequence
import math
from abc import ABC, abstractmethod


class RotationModel(Enum):
    EULER_XYZ = auto()
    EULER_ZYX = auto()
    QUATERNION = auto()
    VECTOR = auto()


class Rotation(ABC):
    @abstractmethod
    def convert(self, target_model: RotationModel) -> Any:
        pass


class QuaternionAngle(Vec4, Rotation):
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, scalar: float, /) -> None: ...

    @overload
    def __init__(self, x: float, y: float, z: float, w: float, /) -> None: ...

    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if len(args) == 0:
            self.scalars = [0.0, 0.0, 0.0, 1.0]

    def to_vector(self):
        x, y, z, w = self.scalars

        angle = 2 * math.acos(max(-1.0, min(1.0, w)))
        sin_half = math.sqrt(max(0.0, 1.0 - w * w))

        if sin_half < 1e-8:
            return VectorAngle(0.0, 0.0, 0.0)

        scale = angle / sin_half
        return VectorAngle(x * scale, y * scale, z * scale)

    def to_euler_xyz(self):
        x, y, z, w = self.scalars

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

        return EulerAngleXYZ(rx, ry, rz)

    def to_euler_zyx(self):
        x, y, z, w = self.scalars

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

        return EulerAngleZYX(rz, ry, rx)

    def convert(self, target_model: RotationModel) -> Any:
        if target_model == RotationModel.QUATERNION:
            return self

        elif target_model == RotationModel.EULER_XYZ:
            return self.to_euler_xyz()

        elif target_model == RotationModel.EULER_ZYX:
            return self.to_euler_zyx()

        elif target_model == RotationModel.VECTOR:
            return self.to_vector()

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")


class VectorAngle(Vec3, Rotation):
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, scalar: float, /) -> None: ...

    @overload
    def __init__(self, x: float, y: float, z: float, /) -> None: ...

    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if len(args) == 0:
            self.scalars = [0.0, 0.0, 0.0]

    def to_quaternion(self):
        x, y, z = self.scalars
        angle = math.sqrt(x*x + y*y + z*z)

        if angle < 1e-8:
            return QuaternionAngle(0.0, 0.0, 0.0, 1.0)

        half_angle = angle * 0.5
        sin_h = math.sin(half_angle)

        quaternion = (
            (x / angle) * sin_h,
            (y / angle) * sin_h,
            (z / angle) * sin_h,
            math.cos(half_angle)
        )

        return QuaternionAngle(*quaternion)

    def to_euler_xyz(self):
        return self.to_quaternion().to_euler_xyz()

    def to_euler_zyx(self):
        return self.to_quaternion().to_euler_zyx()

    def convert(self, target_model: RotationModel) -> Any:
        if target_model == RotationModel.QUATERNION:
            return self.to_quaternion()

        elif target_model == RotationModel.EULER_XYZ:
            return self.to_euler_xyz()

        elif target_model == RotationModel.EULER_ZYX:
            return self.to_euler_zyx()

        elif target_model == RotationModel.VECTOR:
            return self

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")


class EulerAngleXYZ(Vec3, Rotation):
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, scalar: float, /) -> None: ...

    @overload
    def __init__(self, x: float, y: float, z: float, /) -> None: ...

    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if len(args) == 0:
            self.scalars = [0.0, 0.0, 0.0]

    def to_euler_zyx(self):
        return self.to_quaternion().to_euler_zyx()

    def to_vector(self):
        return self.to_quaternion().to_vector()

    def to_quaternion(self):
        x, y, z = self.scalars[0] * 0.5, self.scalars[1] * 0.5, self.scalars[2] * 0.5

        cx, sx = math.cos(x), math.sin(x)
        cy, sy = math.cos(y), math.sin(y)
        cz, sz = math.cos(z), math.sin(z)

        w = cx * cy * cz + sx * sy * sz
        x = sx * cy * cz - cx * sy * sz
        y = cx * sy * cz + sx * cy * sz
        z = cx * cy * sz - sx * sy * cz

        return QuaternionAngle(x, y, z, w)

    def convert(self, target_model: RotationModel) -> Any:
        if target_model == RotationModel.QUATERNION:
            return self.to_quaternion()

        elif target_model == RotationModel.EULER_XYZ:
            return self

        elif target_model == RotationModel.EULER_ZYX:
            return self.to_euler_zyx()

        elif target_model == RotationModel.VECTOR:
            return self.to_vector()

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")

class EulerAngleZYX(Vec3, Rotation):
    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, scalar: float, /) -> None: ...

    @overload
    def __init__(self, x: float, y: float, z: float, /) -> None: ...

    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if len(args) == 0:
            self.scalars = [0.0, 0.0, 0.0]

    def to_euler_xyz(self):
        return self.to_quaternion().to_euler_xyz()

    def to_quaternion(self):
        x, y, z = self.scalars[0] * 0.5, self.scalars[1] * 0.5, self.scalars[2] * 0.5
        
        cz, sz = math.cos(z), math.sin(z)
        cy, sy = math.cos(y), math.sin(y)
        cx, sx = math.cos(x), math.sin(x)

        w = cz * cy * cx + sz * sy * sx
        x = cz * cy * sx - sz * sy * cx
        y = cz * sy * cx + sz * cy * sx
        z = sz * cy * cx - cz * sy * sx

        return QuaternionAngle(x, y, z, w)

    def to_vector(self):
        return self.to_quaternion().to_vector()

    def convert(self, target_model: RotationModel) -> Any:
        if target_model == RotationModel.QUATERNION:
            return self.to_quaternion()

        elif target_model == RotationModel.EULER_XYZ:
            return self.to_euler_xyz()

        elif target_model == RotationModel.EULER_ZYX:
            return self

        elif target_model == RotationModel.VECTOR:
            return self.to_vector()

        raise ValueError(f"Modelo de vetor degenerado. Lendo '{self.model}'")