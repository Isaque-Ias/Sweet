from math import cos, radians, sin, degrees, atan2, pi
from collections.abc import Iterator
from typing import Sequence

class VecN:
    def __init__(self, values: Sequence[float] | float) -> None:
        if isinstance(values, (int, float)):
            values = [values]
        self.scalars = values

    def magnitude(self) -> float:
        return sum(map(lambda scalar: scalar ** 2, self.scalars)) ** .5

    def magnitude_squared(self) -> float:
        return sum(map(lambda scalar: scalar ** 2, self.scalars))

    def normalize(self) -> "VecN":
        magnitude: float = self.magnitude()
        return VecN(*map(lambda scalar: scalar / magnitude, self.scalars))
    
    def dot(self, other: "VecN" | Sequence[int | float]) -> float:
        if isinstance(other, list | tuple | Sequence):
            return sum([self.scalars[i] * other[i] for i in range(len(self.scalars))])
        return sum([self.scalars[i] * other.scalars[i] for i in range(len(self.scalars))])

    def floor(self) -> "VecN":
        return VecN(list(map(lambda scalar: round(scalar), self.scalars)))

    def round(self) -> "VecN":
        return VecN(list(map(lambda scalar: round(scalar), self.scalars)))
    
    def min(self, value: float) -> "VecN":
        return VecN(list(map(lambda scalar: min(scalar, value), self.scalars)))

    def max(self, value: float) -> "VecN":
        return VecN(list(map(lambda scalar: max(scalar, value), self.scalars)))

    def clamp(self, minimum: float, maximum: float) -> "VecN":
        return VecN(list(map(lambda scalar: max(minimum, min(scalar, maximum)), self.scalars)))
    
    def lerp(self, other: "VecN | Sequence[int]", t: float) -> "VecN":
        if isinstance(other, VecN):
            scalars: list[float] = [self.scalars[i] * (1 - t) + other.scalars[i] * t for i in range(len(self.scalars))]
        else:
            scalars: list[float] = [self.scalars[i] * (1 - t) + other[i] * t for i in range(len(self.scalars))]
        return VecN(scalars)
    
    def __add__(self, other: "VecN | Sequence[int | float]") -> "VecN":
        if isinstance(other, VecN):
            scalars: list[float] = [self.scalars[i] + other.scalars[i] for i in range(len(self.scalars))]
        else:
            scalars: list[float] = [self.scalars[i] + other[i] for i in range(len(self.scalars))]
        return VecN(scalars)

    def __neg__(self) -> "VecN":
        return VecN(*map(lambda x: -x, self.scalars))

    def __sub__(self, other: "VecN | Sequence[int | float]") -> "VecN":
        if isinstance(other, VecN):
            scalars: list[float] = [self.scalars[i] - other.scalars[i] for i in range(len(self.scalars))]
        else:
            scalars: list[float] = [self.scalars[i] - other[i] for i in range(len(self.scalars))]
        return VecN(scalars)

    def __mul__(self, other: int | float) -> "VecN":
        return VecN([self.scalars[i] * other for i in range(len(self.scalars))])

    def __rmul__(self, other: int | float) -> "VecN":
        return VecN([self.scalars[i] * other for i in range(len(self.scalars))])
    
    def __truediv__(self, other: int | float) -> "VecN":
        scalars: list[float] = [self.scalars[i] / other for i in range(len(self.scalars))]
        return VecN(scalars)

    def __floordiv__(self, other: int | float) -> "VecN":
        scalars: list[float] = [self.scalars[i] // other for i in range(len(self.scalars))]
        return VecN(scalars)
    
    def __iter__(self) -> Iterator[float]:
        yield from self.scalars

    def unp(self) -> tuple[float, ...]:
        return tuple(self.scalars)
    
    def __getitem__(self, index: int) -> float:
        if index > len(self.scalars) or index < 0:
            raise ValueError("Index fora da lista.")
        return self.scalars[index]

    def __repr__(self) -> str:
        return f'[{self.scalars}]'

class Vec2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def angle(self) -> float:
        ang: float = degrees(atan2(self.y, self.x))
        if ang < 0:
            ang += 360
        return ang

    def rotate(self, angle: float) -> "Vec2":
        return Vec2(self.x * cos(angle * pi / 180) - self.y * sin(angle * pi / 180),
                    self.x * sin(angle * pi / 180) + self.y * cos(angle * pi / 180))
    
    def rotate90(self) -> "Vec2":
        return Vec2(self.y, -self.x)
    
    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** .5

    def magnitude_squared(self) -> float:
        return self.x ** 2 + self.y ** 2

    def normalize(self) -> "Vec2":
        magnitude: float = self.magnitude()
        return Vec2(self.x / magnitude, self.y / magnitude)
    
    def dot(self, other: "Vec2 | Sequence[int | float]") -> float:
        if isinstance(other, list | tuple | Sequence):
            return self.x * other[0] + self.y * other[1]
        return self.x * other.x + self.y * other.y
    
    def cross(self, other: "Vec2 | Sequence[int | float]") -> float:
        if isinstance(other, list | tuple | Sequence):
            return self.x * other[1] - self.y * other[0]
        return self.x * other.y - self.y * other.x

    def mirror_x(self) -> "Vec2":
        return Vec2(-self.x, self.y)

    def mirror_y(self) -> "Vec2":
        return Vec2(self.x, -self.y)

    def floor(self) -> "Vec2":
        return Vec2(int(self.x), int(self.y))

    def round(self) -> "Vec2":
        return Vec2(round(self.x), round(self.y))
    
    def min(self, value: float) -> "Vec2":
        return Vec2(min(self.x, value), min(self.y, value))

    def max(self, value: float) -> "Vec2":
        return Vec2(max(self.x, value), max(self.y, value))

    def clamp(self, minimum: float, maximum: float) -> "Vec2":
        return Vec2(max(min(self.x, maximum), minimum), max(min(self.y, maximum), minimum))

    def __add__(self, other: "Vec2 | Sequence[int| float]") -> "Vec2":
        if isinstance(other, Vec2):
            return Vec2(self.x + other.x, self.y + other.y)
        return Vec2(self.x + other[0], self.y + other[1])

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def __sub__(self, other: "Vec2 | Sequence[int| float]") -> "Vec2":
        if isinstance(other, Vec2):
            return Vec2(self.x - other.x, self.y - other.y)
        return Vec2(self.x + other[0], self.y + other[1])

    def __mul__(self, other: int | float) -> "Vec2":
        return Vec2(self.x * other, self.y * other)

    def __rmul__(self, other: int | float) -> "Vec2":
        return Vec2(self.x * other, self.y * other)
    
    def __truediv__(self, other: int | float) -> "Vec2":
        return Vec2(self.x / other, self.y / other)

    def __floordiv__(self, other: int | float) -> "Vec2":
        return Vec2(self.x // other, self.y // other)
    
    def __iter__(self):
        yield self.x
        yield self.y

    def unp(self) -> tuple[float, float]:
        return (self.x, self.y)
    
    def __getitem__(self, index: int) -> float:
        if index > 1 or index < 0:
            raise ValueError("Index fora da lista.")
        return self.x if index == 0 else self.y

    def __repr__(self) -> str:
        return f'[{self.x}, {self.y}]'
    

class Vec3:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z

    def direction(self) -> "Vec3":
        vec = Vec3(
            sin(radians(self.x)) * cos(radians(self.y)),
            sin(radians(self.y)),
            cos(radians(self.x)) * cos(radians(self.y)),
        )

        return vec
    
    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** .5

    def magnitude_squared(self) -> float:
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def normalize(self) -> "Vec3":
        magnitude: float = self.magnitude()
        return Vec3(self.x / magnitude, self.y / magnitude, self.z / magnitude)

    def dot(self, other: "Vec3" | Sequence[int | float]) -> float:
        if isinstance(other, list | tuple | Sequence):
            return self.x * other[0] + self.y * other[1] + self.z * other[2]
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: "Vec3" | Sequence[int | float]) -> "Vec3":
        if isinstance(other, list | tuple | Sequence):
            return Vec3(self.x * other[1] - self.y * other[0],
                    self.x * other[2] - self.z * other[0],
                    self.y * other[2] - self.z * other[1])
        return Vec3(self.x * other.y - self.y * other.x,
                    self.x * other.z - self.z * other.x,
                    self.y * other.z - self.z * other.y)

    def floor(self) -> "Vec3":
        return Vec3(int(self.x), int(self.y), int(self.z))

    def round(self) -> "Vec3":
        return Vec3(round(self.x), round(self.y), round(self.z))

    def min(self, value: float) -> "Vec3":
        return Vec3(min(self.x, value), min(self.y, value), min(self.z, value))

    def max(self, value: float) -> "Vec3":
        return Vec3(max(self.x, value), max(self.y, value), max(self.z, value))

    def clamp(self, minimum: float, maximum: float) -> "Vec3":
        return Vec3(max(min(self.x, maximum), minimum), max(min(self.y, maximum), minimum), max(min(self.z, maximum), minimum))

    def __add__(self, other: "Vec3" | Sequence[int | float]) -> "Vec3":
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __sub__(self, other: "Vec3" | Sequence[int | float]) -> "Vec3":
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])

    def __mul__(self, other: int | float) -> "Vec3":
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other: int | float) -> "Vec3":
        return Vec3(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other: int | float) -> "Vec3":
        return Vec3(self.x / other, self.y / other, self.z / other)

    def __floordiv__(self, other: int | float) -> "Vec3":
        return Vec3(self.x // other, self.y // other, self.z // other)
    
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
    
    def __getitem__(self, index: int) -> float:
        if index > 2 or index < 0:
            raise ValueError("Index fora da lista.")
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        else:
            return self.z

    def unp(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __repr__(self) -> str:
        return f'[{self.x}, {self.y}, {self.z}]'