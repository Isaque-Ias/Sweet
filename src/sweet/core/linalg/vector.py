from __future__ import annotations
from abc import ABC
from collections.abc import Iterator, Sequence, Iterable
from math import cos, sin, radians, degrees, atan2, floor as math_floor
from typing import Union, Type, Self, overload, Any, cast

VectorLike = Union["Vec", Sequence[Union[int, float]]]

class Vec(ABC):
    scalars: list[float]
    
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, scalar: float, /) -> None: ...
    @overload
    def __init__(self, *args: float) -> None: ...
    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        if len(args) == 0:
            self.scalars = []
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, (list, tuple, Sequence)):
                arg = cast(list[int | float], arg)
                self.scalars = [float(x) for x in arg]
            elif isinstance(arg, (int, float)):
                self.scalars = [float(arg)]
            else:
                raise TypeError("Argumento único deve ser um número ou uma sequência numérica.")
        else:
            self.scalars = [float(x) for x in args]

    @classmethod
    def from_iter(cls: Type[Self], values: Iterable[float]) -> Self:
        return cls(list(values))

    @property
    def dim(self) -> int:
        return len(self.scalars)

    def magnitude(self) -> float:
        return sum(x ** 2 for x in self.scalars) ** 0.5

    def magnitude_squared(self) -> float:
        return sum(x ** 2 for x in self.scalars)

    def normalize(self: Self) -> Self:
        mag = self.magnitude()
        if mag == 0:
            raise ZeroDivisionError("Cannot normalize a zero-length vector.")
        return self.__class__([x / mag for x in self.scalars])

    def dot(self, other: VectorLike) -> float:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        if len(other_vals) != self.dim:
            raise ValueError(f"Vector dimensions must match ({self.dim} vs {len(other_vals)}).")
        return sum(a * b for a, b in zip(self.scalars, other_vals))

    def floor(self: Self) -> Self:
        return self.__class__([float(math_floor(x)) for x in self.scalars])

    def round(self: Self) -> Self:
        return self.__class__([float(round(x)) for x in self.scalars])

    def min(self: Self, value: float) -> Self:
        return self.__class__([min(x, value) for x in self.scalars])

    def max(self: Self, value: float) -> Self:
        return self.__class__([max(x, value) for x in self.scalars])

    def clamp(self: Self, minimum: float, maximum: float) -> Self:
        return self.__class__([max(minimum, min(x, maximum)) for x in self.scalars])

    def lerp(self: Self, other: VectorLike, t: float) -> Self:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        return self.__class__([
            a * (1.0 - t) + b * t for a, b in zip(self.scalars, other_vals)
        ])

    def __add__(self: Self, other: VectorLike) -> Self:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        return self.__class__([a + b for a, b in zip(self.scalars, other_vals)])

    def __sub__(self: Self, other: VectorLike) -> Self:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        return self.__class__([a - b for a, b in zip(self.scalars, other_vals)])

    def __neg__(self: Self) -> Self:
        return self.__class__([-x for x in self.scalars])

    def __mul__(self: Self, other: float) -> Self:
        return self.__class__([x * other for x in self.scalars])

    def __rmul__(self: Self, other: float) -> Self:
        return self * other

    def __truediv__(self: Self, other: float) -> Self:
        return self.__class__([x / other for x in self.scalars])

    def __floordiv__(self: Self, other: float) -> Self:
        return self.__class__([x // other for x in self.scalars])

    def __iter__(self) -> Iterator[float]:
        return iter(self.scalars)

    def unp(self) -> tuple[float, ...]:
        return tuple(self.scalars)

    def __getitem__(self, index: int) -> float:
        if not (0 <= index < self.dim):
            raise IndexError("Index fora da lista.")
        return self.scalars[index]

    def __setitem__(self, index: int, value: float) -> None:
        if not (0 <= index < self.dim):
            raise IndexError("Index fora da lista.")
        self.scalars[index] = float(value)

    def __repr__(self) -> str:
        return f"{self.scalars}"

class VecN(Vec):
    pass


class Vec2(Vec):
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, scalar: float, /) -> None: ...
    @overload
    def __init__(self, x: float, y: float, /) -> None: ...
    @overload
    def __init__(self, iterable: Sequence[float], /) -> None: ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if len(self.scalars) == 0:
            self.scalars = [0.0, 0.0]
        elif len(self.scalars) == 1:
            val = self.scalars[0]
            self.scalars = [val, val]
        elif len(self.scalars) != 2:
            raise ValueError(f"Instanciação inválida. Vec2 exige exatamente 2 dimensões. Recebeu {len(self.scalars)}")

    @property
    def x(self) -> float:
        return self.scalars[0]

    @x.setter
    def x(self, val: float) -> None:
        self.scalars[0] = float(val)

    @property
    def y(self) -> float:
        return self.scalars[1]

    @y.setter
    def y(self, val: float) -> None:
        self.scalars[1] = float(val)

    def angle(self) -> float:
        ang = degrees(atan2(self.y, self.x))
        return ang + 360.0 if ang < 0 else ang

    def rotate(self, angle_deg: float) -> Vec2:
        rad = radians(angle_deg)
        cos_a, sin_a = cos(rad), sin(rad)
        return Vec2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def rotate90(self) -> Vec2:
        return Vec2(self.y, -self.x)

    def cross(self, other: VectorLike) -> float:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        return self.x * other_vals[1] - self.y * other_vals[0]

    def mirror_x(self) -> Vec2:
        return Vec2(-self.x, self.y)

    def mirror_y(self) -> Vec2:
        return Vec2(self.x, -self.y)


class Vec3(Vec):
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
        if len(self.scalars) == 0:
            self.scalars = [0.0, 0.0, 0.0]
        elif len(self.scalars) == 1:
            val = self.scalars[0]
            self.scalars = [val, val, val]
        elif len(self.scalars) != 3:
            raise ValueError(f"Instanciação inválida. Vec3 exige exatamente 3 dimensões. Recebeu {len(self.scalars)}")

    @property
    def x(self) -> float:
        return self.scalars[0]

    @x.setter
    def x(self, val: float) -> None:
        self.scalars[0] = float(val)

    @property
    def y(self) -> float:
        return self.scalars[1]

    @y.setter
    def y(self, val: float) -> None:
        self.scalars[1] = float(val)

    @property
    def z(self) -> float:
        return self.scalars[2]

    @z.setter
    def z(self, val: float) -> None:
        self.scalars[2] = float(val)

    def direction(self) -> Vec3:
        rad_x, rad_y = radians(self.x), radians(self.y)
        return Vec3(
            sin(rad_x) * cos(rad_y),
            sin(rad_y),
            cos(rad_x) * cos(rad_y)
        )

    def cross(self, other: VectorLike) -> Vec3:
        other_vals = list(other) if not isinstance(other, Vec) else other.scalars
        ox, oy, oz = other_vals[0], other_vals[1], other_vals[2]
        return Vec3(
            self.y * oz - self.z * oy,
            self.z * ox - self.x * oz,
            self.x * oy - self.y * ox
        )
