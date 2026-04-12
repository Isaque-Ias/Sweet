from math import cos, sin, degrees, atan2, pi
from typing import Sequence
from numbers import Real

class VecN:
    def __init__(self, values: Sequence[Real]) -> None:
        self.scalars = values

    def magnitude(self) -> Real:
        return sum(map(lambda scalar: scalar ** 2, self.scalars)) ** .5

    def magnitude_squared(self) -> Real:
        return sum(map(lambda scalar: scalar ** 2, self.scalars))

    def normalize(self) -> "VecN":
        magnitude: Real = self.magnitude()
        return VecN(*map(lambda scalar: scalar / magnitude, self.scalars))
    
    def dot(self, other: "VecN") -> Real:
        products: list[Real] = [self.scalars[i] * other.scalars[i] for i in range(len(self.scalars))]
        return sum(products)

    def floor(self) -> "VecN":
        return VecN(list(map(lambda scalar: round(scalar), self.scalars)))

    def round(self) -> "VecN":
        return VecN(list(map(lambda scalar: round(scalar), self.scalars)))
    
    def min(self, value: Real) -> "VecN":
        return VecN(list(map(lambda scalar: min(scalar, value), self.scalars)))

    def max(self, value: Real) -> "VecN":
        return VecN(list(map(lambda scalar: max(scalar, value), self.scalars)))

    def clamp(self, minimum: Real, maximum: Real) -> "VecN":
        return VecN(list(map(lambda scalar: max(minimum, min(scalar, maximum)), self.scalars)))
    
    def lerp(self, other, t) -> "VecN":
        if isinstance(other, VecN):
            scalars: list[Real] = [self.scalars[i] * (1 - t) + other.scalars[i] * t for i in range(len(self.scalars))]
        else:
            scalars: list[Real] = [self.scalars[i] * (1 - t) + other[i] * t for i in range(len(self.scalars))]
        return VecN(scalars)
    
    def __add__(self, other) -> "VecN":
        if isinstance(other, VecN):
            scalars: list[Real] = [self.scalars[i] + other.scalars[i] for i in range(len(self.scalars))]
        else:
            scalars: list[Real] = [self.scalars[i] + other[i] for i in range(len(self.scalars))]
        return VecN(scalars)

    def __neg__(self) -> "VecN":
        return VecN(*map(lambda x: -x, self.scalars))

    def __sub__(self, other) -> "VecN":
        if isinstance(other, VecN):
            scalars: list[Real] = [self.scalars[i] - other.scalars[i] for i in range(len(self.scalars))]
        else:
            scalars: list[Real] = [self.scalars[i] - other[i] for i in range(len(self.scalars))]
        return VecN(scalars)

    def __mul__(self, other) -> "VecN":
        scalars: list[Real] = [self.scalars[i] * other for i in range(len(self.scalars))]
        return VecN(scalars)

    def __rmul__(self, other) -> "VecN":
        scalars: list[Real] = [self.scalars[i] * other for i in range(len(self.scalars))]
        return VecN(scalars)
    
    def __truediv__(self, other) -> "VecN":
        scalars: list[Real] = [self.scalars[i] / other for i in range(len(self.scalars))]
        return VecN(scalars)

    def __floordiv__(self, other) -> "VecN":
        scalars: list[Real] = [self.scalars[i] // other for i in range(len(self.scalars))]
        return VecN(scalars)
    
    def unp(self) -> tuple[Real, Real]:
        return tuple(self.scalars)
    
    def __getitem__(self, index: int) -> Real:
        if index > len(self.scalars) or index < 0:
            raise ValueError("Index fora da lista.")
        return self.scalars[index]

    def __repr__(self) -> str:
        return f'[{self.scalars}]'

class Vec:
    def __init__(self, x: Real, y: Real) -> None:
        self.x = x
        self.y = y

    def angle(self) -> Real:
        ang: Real = degrees(atan2(self.y, self.x))
        if ang < 0:
            ang += 360
        return ang

    def rotate(self, angle: Real) -> "Vec":
        return Vec(self.x * cos(angle * pi / 180) - self.y * sin(angle * pi / 180),
                   self.x * sin(angle * pi / 180) + self.y * cos(angle * pi / 180))
    
    def rotate90(self) -> "Vec":
        return Vec(self.y, -self.x)
    
    def magnitude(self) -> "Vec":
        return (self.x ** 2 + self.y ** 2) ** .5

    def magnitude_squared(self) -> "Vec":
        return self.x ** 2 + self.y ** 2

    def normalize(self) -> "Vec":
        magnitude: Real = self.magnitude()
        return Vec(self.x / magnitude, self.y / magnitude)
    
    def dot(self, other) -> Real:
        return self.x * other.x + self.y * other.y
    
    def cross(self, other) -> Real:
        return self.x * other.y - self.y * other.x

    def mirror_x(self) -> "Vec":
        return Vec(-self.x, self.y)

    def mirror_y(self) -> "Vec":
        return Vec(self.x, -self.y)

    def floor(self) -> "Vec":
        return Vec(int(self.x), int(self.y))

    def round(self) -> "Vec":
        return Vec(round(self.x), round(self.y))
    
    def min(self, value: Real) -> "Vec":
        return Vec(min(self.x, value), min(self.y, value))

    def max(self, value: Real) -> "Vec":
        return Vec(max(self.x, value), max(self.y, value))

    def clamp(self, minimum: Real, maximum: Real) -> "Vec":
        return Vec(max(min(self.x, maximum), minimum), max(min(self.y, maximum), minimum))

    def __add__(self, other) -> "Vec":
        if isinstance(other, Vec):
            return Vec(self.x + other.x, self.y + other.y)
        return Vec(self.x + other[0], self.y + other[1])

    def __neg__(self) -> "Vec":
        return Vec(-self.x, -self.y)

    def __sub__(self, other) -> "Vec":
        if isinstance(other, Vec):
            return Vec(self.x - other.x, self.y - other.y)
        return Vec(self.x + other[0], self.y + other[1])

    def __mul__(self, other) -> "Vec":
        return Vec(self.x * other, self.y * other)

    def __rmul__(self, other) -> "Vec":
        return Vec(self.x * other, self.y * other)
    
    def __truediv__(self, other) -> "Vec":
        return Vec(self.x / other, self.y / other)

    def __floordiv__(self, other) -> "Vec":
        return Vec(self.x // other, self.y // other)
    
    def unp(self) -> tuple[Real, Real]:
        return (self.x, self.y)
    
    def __getitem__(self, index: int) -> Real:
        if index > 1 or index < 0:
            raise ValueError("Index fora da lista.")
        return self.x if index == 0 else self.y

    def __repr__(self) -> str:
        return f'[{self.x}, {self.y}]'