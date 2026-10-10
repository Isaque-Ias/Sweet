import math
from dataclasses import dataclass, field
from typing import List, Optional


class Vec2:
    """2D Vector utility class for physics calculations."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return self * scalar

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x / scalar, self.y / scalar)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.length_sq())

    def normalized(self) -> "Vec2":
        l = self.length()
        return Vec2(0.0, 0.0) if l == 0 else self / l

    def __repr__(self):
        return f"Vec2({self.x:.3f}, {self.y:.3f})"


# -------------------------------------------------------------------
# Shapes & Rigid Bodies
# -------------------------------------------------------------------


class Shape:
    """Base collision shape."""

    pass


class CircleShape(Shape):
    def __init__(self, radius: float):
        self.radius = radius


class BoxShape(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height


class RigidBody:

    def __init__(
        self,
        position: Vec2,
        mass: float = 1.0,
        shape: Optional[Shape] = None,
        restitution: float = 0.5,
        friction: float = 0.2,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ):
        self.position = position
        self.velocity = Vec2(0.0, 0.0)
        self.force = Vec2(0.0, 0.0)
        self.mass = mass
        self.inv_mass = 0.0 if mass <= 0 else 1.0 / mass
        self.shape = shape
        self.restitution = restitution
        self.friction = friction

        # Collision Regions / Bitmask Filtering
        self.collision_category = collision_category
        self.collision_mask = collision_mask

    def apply_force(self, force: Vec2):
        self.force = self.force + force

    def can_collide_with(self, other: "RigidBody") -> bool:
        return bool(
            (self.collision_category & other.collision_mask)
            and (other.collision_category & self.collision_mask)
        )


# -------------------------------------------------------------------
# Collision Manifold, Resolution & Response
# -------------------------------------------------------------------


@dataclass
class CollisionManifold:
    """Holds collision manifold geometric data and methods for resolution/response."""

    body_a: RigidBody
    body_b: RigidBody
    normal: Vec2  # Unit direction vector from A to B
    penetration: float  # Overlap distance
    contact_points: List[Vec2] = field(default_factory=list)

    def resolve_resolution(self, percent: float = 0.8, slop: float = 0.01):
        """
        Collision Resolution (Positional De-penetration).
        Separates overlapping bodies using linear Baumgarte projection.
        """
        inv_mass_sum = self.body_a.inv_mass + self.body_b.inv_mass
        if inv_mass_sum == 0:
            return

        correction_mag = (
            max(self.penetration - slop, 0.0) / inv_mass_sum * percent
        )
        correction = self.normal * correction_mag

        if self.body_a.inv_mass > 0:
            self.body_a.position = self.body_a.position - (
                correction * self.body_a.inv_mass
            )
        if self.body_b.inv_mass > 0:
            self.body_b.position = self.body_b.position + (
                correction * self.body_b.inv_mass
            )

    def resolve_response(self):
        """
        Collision Response (Impulse Calculation).
        Calculates and applies dynamic linear elasticity (restitution) and friction impulses.
        """
        inv_mass_sum = self.body_a.inv_mass + self.body_b.inv_mass
        if inv_mass_sum == 0:
            return

        # 1. Normal Impulse (Elasticity / Bounce)
        rel_vel = self.body_b.velocity - self.body_a.velocity
        vel_along_normal = rel_vel.dot(self.normal)

        # Skip if bodies are moving apart
        if vel_along_normal > 0:
            return

        e = min(self.body_a.restitution, self.body_b.restitution)
        j = -(1.0 + e) * vel_along_normal / inv_mass_sum
        impulse = self.normal * j

        if self.body_a.inv_mass > 0:
            self.body_a.velocity = self.body_a.velocity - (
                impulse * self.body_a.inv_mass
            )
        if self.body_b.inv_mass > 0:
            self.body_b.velocity = self.body_b.velocity + (
                impulse * self.body_b.inv_mass
            )

        # 2. Tangential Impulse (Friction)
        rel_vel_post = self.body_b.velocity - self.body_a.velocity
        tangent = rel_vel_post - (self.normal * rel_vel_post.dot(self.normal))

        if tangent.length_sq() > 1e-6:
            tangent = tangent.normalized()
            jt = -rel_vel_post.dot(tangent) / inv_mass_sum

            # Coulomb friction clamping
            mu = math.sqrt(self.body_a.friction * self.body_b.friction)
            jt = max(-j * mu, min(jt, j * mu))

            friction_impulse = tangent * jt
            if self.body_a.inv_mass > 0:
                self.body_a.velocity = self.body_a.velocity - (
                    friction_impulse * self.body_a.inv_mass
                )
            if self.body_b.inv_mass > 0:
                self.body_b.velocity = self.body_b.velocity + (
                    friction_impulse * self.body_b.inv_mass
                )


# -------------------------------------------------------------------
# Collision Narrowphase Operations
# -------------------------------------------------------------------


def check_collision(
    a: RigidBody, b: RigidBody
) -> Optional[CollisionManifold]:
    """Evaluates narrowphase collision between two bodies and returns a CollisionManifold."""
    if not a.shape or not b.shape or not a.can_collide_with(b):
        return None

    # Circle vs Circle
    if isinstance(a.shape, CircleShape) and isinstance(b.shape, CircleShape):
        diff = b.position - a.position
        dist = diff.length()
        radius_sum = a.shape.radius + b.shape.radius
        if dist < radius_sum:
            normal = diff.normalized() if dist > 0 else Vec2(1, 0)
            penetration = radius_sum - dist
            contact = a.position + (normal * a.shape.radius)
            return CollisionManifold(a, b, normal, penetration, [contact])

    # Circle vs Box
    elif isinstance(a.shape, CircleShape) and isinstance(b.shape, BoxShape):
        return _circle_box_collision(a, b, circle_is_a=True)
    elif isinstance(a.shape, BoxShape) and isinstance(b.shape, CircleShape):
        return _circle_box_collision(b, a, circle_is_a=False)

    # Box vs Box (AABB)
    elif isinstance(a.shape, BoxShape) and isinstance(b.shape, BoxShape):
        dx = b.position.x - a.position.x
        overlap_x = (a.shape.width / 2 + b.shape.width / 2) - abs(dx)
        if overlap_x <= 0:
            return None

        dy = b.position.y - a.position.y
        overlap_y = (a.shape.height / 2 + b.shape.height / 2) - abs(dy)
        if overlap_y <= 0:
            return None

        if overlap_x < overlap_y:
            normal = Vec2(1.0 if dx > 0 else -1.0, 0.0)
            penetration = overlap_x
        else:
            normal = Vec2(0.0, 1.0 if dy > 0 else -1.0)
            penetration = overlap_y

        contact = a.position + normal * (penetration / 2)
        return CollisionManifold(a, b, normal, penetration, [contact])

    return None


def _circle_box_collision(
    circle_body: RigidBody, box_body: RigidBody, circle_is_a: bool
) -> Optional[CollisionManifold]:
    c_shape: CircleShape = circle_body.shape
    b_shape: BoxShape = box_body.shape

    half_w, half_h = b_shape.width / 2, b_shape.height / 2
    clamped_x = max(
        box_body.position.x - half_w,
        min(circle_body.position.x, box_body.position.x + half_w),
    )
    clamped_y = max(
        box_body.position.y - half_h,
        min(circle_body.position.y, box_body.position.y + half_h),
    )

    closest = Vec2(clamped_x, clamped_y)
    diff = circle_body.position - closest
    dist_sq = diff.length_sq()

    if dist_sq < c_shape.radius * c_shape.radius:
        dist = math.sqrt(dist_sq)
        normal = diff / dist if dist > 0 else Vec2(0, 1)
        penetration = c_shape.radius - dist

        if circle_is_a:
            return CollisionManifold(
                circle_body, box_body, normal * -1.0, penetration, [closest]
            )
        else:
            return CollisionManifold(
                box_body, circle_body, normal, penetration, [closest]
            )

    return None


# -------------------------------------------------------------------
# User Constraints Interface
# -------------------------------------------------------------------


class Constraint:
    """Base class to define custom joint / physics constraints."""

    def solve(self, dt: float):
        raise NotImplementedError


class DistanceConstraint(Constraint):
    """Enforces a rigid target distance between two bodies."""

    def __init__(
        self,
        body_a: RigidBody,
        body_b: RigidBody,
        distance: float,
        stiffness: float = 0.5,
    ):
        self.body_a = body_a
        self.body_b = body_b
        self.distance = distance
        self.stiffness = stiffness

    def solve(self, dt: float):
        delta = self.body_b.position - self.body_a.position
        current_dist = delta.length()
        if current_dist == 0:
            return

        error = current_dist - self.distance
        correction = delta.normalized() * (error * self.stiffness)

        inv_mass_sum = self.body_a.inv_mass + self.body_b.inv_mass
        if inv_mass_sum == 0:
            return

        if self.body_a.inv_mass > 0:
            self.body_a.position = self.body_a.position + (
                correction * (self.body_a.inv_mass / inv_mass_sum)
            )
        if self.body_b.inv_mass > 0:
            self.body_b.position = self.body_b.position - (
                correction * (self.body_b.inv_mass / inv_mass_sum)
            )


# -------------------------------------------------------------------
# World Manager
# -------------------------------------------------------------------


class PhysicsWorld:

    def __init__(self, gravity: Vec2 = Vec2(0.0, -9.81)):
        self.gravity = gravity
        self.bodies: List[RigidBody] = []
        self.constraints: List[Constraint] = []

    def add_body(self, body: RigidBody):
        self.bodies.append(body)

    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)

    def tick(self, dt: float):
        """Advances the virtual physics simulation by an interval dt."""
        if dt <= 0:
            return

        # 1. Force Integration
        for body in self.bodies:
            if body.inv_mass > 0:
                accel = self.gravity + (body.force * body.inv_mass)
                body.velocity = body.velocity + (accel * dt)
                body.force = Vec2(0, 0)

        # 2. Collision Detection & Manifold Handling
        manifolds: List[CollisionManifold] = []
        for i in range(len(self.bodies)):
            for j in range(i + 1, len(self.bodies)):
                manifold = check_collision(self.bodies[i], self.bodies[j])
                if manifold:
                    manifolds.append(manifold)

        # Resolve impulse response & positional overlap
        for manifold in manifolds:
            manifold.resolve_response()
            manifold.resolve_resolution()

        # 3. Constraint Solving
        for constraint in self.constraints:
            constraint.solve(dt)

        # 4. Position Integration
        for body in self.bodies:
            if body.inv_mass > 0:
                body.position = body.position + (body.velocity * dt)