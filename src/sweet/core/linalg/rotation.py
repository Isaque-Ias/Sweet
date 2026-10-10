from enum import Enum, auto
from .vector import Vec3, Vec4
from typing import Any, Self, overload, Sequence
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

    @classmethod
    def from_axis_angle(cls, axis: Sequence[float], angle: float, radians: bool = True) -> "QuaternionAngle":
        """Creates a quaternion from a 3D vector axis and an angle."""
        if not radians:
            angle = math.radians(angle)

        ax, ay, az = axis
        length = math.sqrt(ax * ax + ay * ay + az * az)
        if length < 1e-8:
            return cls(0.0, 0.0, 0.0, 1.0)

        half_angle = angle * 0.5
        sin_half = math.sin(half_angle)
        scale = sin_half / length

        q = cls(ax * scale, ay * scale, az * scale, math.cos(half_angle))
        return q

    def normalize(self) -> Self:
        """Normalizes the quaternion in-place and returns self."""
        x, y, z, w = self.scalars
        length = math.sqrt(x * x + y * y + z * z + w * w)
        if length > 1e-8:
            self.scalars = [x / length, y / length, z / length, w / length]
        else:
            self.scalars = [0.0, 0.0, 0.0, 1.0]
        return self

    def get_forward(self) -> tuple[float, float, float]:
        x, y, z, w = self.scalars
        fx = -2.0 * (x * z + w * y)
        fy = -2.0 * (y * z - w * x)
        fz = -1.0 + 2.0 * (x * x + y * y)
        return Vec3(fx, fy, fz)

    def get_up(self) -> tuple[float, float, float]:
        x, y, z, w = self.scalars
        ux = 2.0 * (x * y - w * z)
        uy = 1.0 - 2.0 * (x * x + z * z)
        uz = 2.0 * (y * z + w * x)
        return Vec3(ux, uy, uz)

    def get_right(self) -> tuple[float, float, float]:
        x, y, z, w = self.scalars
        rx = 1.0 - 2.0 * (y * y + z * z)
        ry = 2.0 * (x * y + w * z)
        rz = 2.0 * (x * z - w * y)
        return Vec3(rx, ry, rz)

    def __mul__(self, other: "QuaternionAngle") -> "QuaternionAngle":
        """Hamilton product (q1 * q2) for applying local rotations."""
        x1, y1, z1, w1 = self.scalars
        x2, y2, z2, w2 = other.scalars

        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2

        res = QuaternionAngle(x, y, z, w)
        return res.normalize()

    def rotate_pitch(self, angle: float, radians: bool = True) -> Self:
        """Rotates around local Right axis (X-axis). Positive pitch looks UP."""
        q_pitch = QuaternionAngle.from_axis_angle((1.0, 0.0, 0.0), angle, radians=radians)
        
        new_q = self * q_pitch
        self.scalars = new_q.scalars
        return self

    def rotate_yaw(
        self, 
        angle: float, 
        fixed: bool = True, 
        world_up: Sequence[float] = (0.0, 1.0, 0.0), 
        radians: bool = True
    ) -> Self:
        if fixed:
            q_yaw = QuaternionAngle.from_axis_angle(world_up, angle, radians=radians)
            new_q = q_yaw * self
        else:
            q_yaw = QuaternionAngle.from_axis_angle((0.0, 1.0, 0.0), angle, radians=radians)
            new_q = self * q_yaw

        self.scalars = new_q.scalars
        return self

    def rotate_vertical(self, angle: float, radians: bool = False) -> Self:
        return self.rotate_pitch(angle, radians=radians)

    def rotate_horizontal(
        self, 
        angle: float, 
        fixed: bool = True, 
        world_up: Sequence[float] = (0.0, 1.0, 0.0), 
        radians: bool = False
    ) -> Self:
        return self.rotate_yaw(angle, fixed=fixed, world_up=world_up, radians=radians)

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