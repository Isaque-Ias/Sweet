"""
Camera System Module

Enhanced camera system with:
- Original basic camera functionality (Cam, Camera classes)
- Camera animations and tweening with easing functions
- Camera shake effects using Perlin noise
- Viewport culling for performance optimization
- Parallax layer system for depth-based scrolling
- Camera follow patterns (lerp, leading, predicted)
- Camera bounds/clamp regions
- Camera zoom animations
"""

from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple
from enum import Enum
import math

# ============================================================================
# ORIGINAL CAMERA SYSTEM (Backward Compatible)
# ============================================================================


class Cam:
    """Original camera class for backward compatibility."""

    def __init__(self, pos: tuple, scale: tuple, angle: int, name: str) -> None:
        self.set_name(name)
        self.set_pos(pos)
        self.set_scale(scale)
        self.set_angle(angle)

    def set_pos(self, pos: tuple) -> None:
        self._pos = pos

    def set_scale(self, scale: tuple) -> None:
        self._scale = scale

    def set_angle(self, angle: str) -> None:
        self._angle = angle

    def set_name(self, name: str) -> None:
        self._name = name

    def get_pos(self) -> tuple:
        return self._pos

    def get_scale(self) -> tuple:
        return self._scale

    def get_angle(self) -> int:
        return self._angle

    def get_name(self) -> str:
        return self._name


class CameraManager:
    """Original camera manager for backward compatibility."""

    _cams: dict[str, Cam] = {"main": Cam([0, 0], [1, 1], 0, "main")}
    _main: str = "main"

    @classmethod
    def create_cam(cls, name: str) -> Cam:
        if cls._cams.get(name):
            raise KeyError

        cam = Cam([0, 0], [0, 0], 0, name)
        cls._cams[name] = cam
        return cam

    @classmethod
    def destroy_cam(cls, name: str) -> None:
        cls._cams.pop(name)

    @classmethod
    def set_main_camera(cls, name: str) -> None:
        cls._main = name

    @classmethod
    def get_main_camera(cls) -> Cam:
        return cls._cams[cls._main]

    @classmethod
    def get_camera(cls, name: str) -> Cam:
        return cls._cams[name]


# Keep Camera as alias for backward compatibility
Camera = CameraManager


# ============================================================================
# ENHANCED CAMERA SYSTEM (New Features)
# ============================================================================


class EaseType(Enum):
    """Easing function types."""

    LINEAR = "linear"
    EASE_IN_QUAD = "ease_in_quad"
    EASE_OUT_QUAD = "ease_out_quad"
    EASE_IN_OUT_QUAD = "ease_in_out_quad"
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"
    EASE_IN_SINE = "ease_in_sine"
    EASE_OUT_SINE = "ease_out_sine"
    EASE_IN_OUT_SINE = "ease_in_out_sine"


class Easing:
    """Easing functions for animations."""

    @staticmethod
    def linear(t: float) -> float:
        """Linear easing (no easing)."""
        return t

    @staticmethod
    def ease_in_quad(t: float) -> float:
        """Quadratic ease-in."""
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        """Quadratic ease-out."""
        return 1 - (1 - t) ** 2

    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        """Quadratic ease-in-out."""
        if t < 0.5:
            return 2 * t * t
        return 1 - (-2 * t + 2) ** 2 / 2

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        """Cubic ease-in."""
        return t**3

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        """Cubic ease-out."""
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Cubic ease-in-out."""
        if t < 0.5:
            return 4 * t**3
        return 1 - (-2 * t + 2) ** 3 / 2

    @staticmethod
    def ease_in_sine(t: float) -> float:
        """Sine ease-in."""
        return 1 - math.cos((t * math.pi) / 2)

    @staticmethod
    def ease_out_sine(t: float) -> float:
        """Sine ease-out."""
        return math.sin((t * math.pi) / 2)

    @staticmethod
    def ease_in_out_sine(t: float) -> float:
        """Sine ease-in-out."""
        return -(math.cos(math.pi * t) - 1) / 2

    @staticmethod
    def get_easing_function(ease_type: EaseType) -> Callable[[float], float]:
        """Get easing function by type."""
        functions = {
            EaseType.LINEAR: Easing.linear,
            EaseType.EASE_IN_QUAD: Easing.ease_in_quad,
            EaseType.EASE_OUT_QUAD: Easing.ease_out_quad,
            EaseType.EASE_IN_OUT_QUAD: Easing.ease_in_out_quad,
            EaseType.EASE_IN_CUBIC: Easing.ease_in_cubic,
            EaseType.EASE_OUT_CUBIC: Easing.ease_out_cubic,
            EaseType.EASE_IN_OUT_CUBIC: Easing.ease_in_out_cubic,
            EaseType.EASE_IN_SINE: Easing.ease_in_sine,
            EaseType.EASE_OUT_SINE: Easing.ease_out_sine,
            EaseType.EASE_IN_OUT_SINE: Easing.ease_in_out_sine,
        }
        return functions.get(ease_type, Easing.linear)


@dataclass
class Vec2:
    """2D vector."""

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def distance_to(self, other: "Vec2") -> float:
        """Calculate distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def lerp(self, other: "Vec2", t: float) -> "Vec2":
        """Linear interpolation."""
        return Vec2(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)


class PerlinNoise:
    """Simple Perlin noise for camera shake."""

    def __init__(self, seed: int = 42):
        """Initialize Perlin noise."""
        self.seed = seed
        self.permutation = list(range(256))
        import random

        random.Random(seed).shuffle(self.permutation)
        self.permutation += self.permutation

    def noise(self, x: float, y: float = 0.0, z: float = 0.0) -> float:
        """Generate Perlin noise value."""
        xi = int(x) & 255
        yi = int(y) & 255
        zi = int(z) & 255

        xf = x - int(x)
        yf = y - int(y)
        zf = z - int(z)

        u = self._fade(xf)
        v = self._fade(yf)
        w = self._fade(zf)

        p = self.permutation
        aa = p[p[xi] + yi]
        ab = p[p[xi] + yi + 1]
        ba = p[p[xi + 1] + yi]
        bb = p[p[xi + 1] + yi + 1]

        result = self._lerp(
            self._lerp(
                self._grad(p[aa + zi], xf, yf, zf),
                self._grad(p[ba + zi], xf - 1, yf, zf),
                u,
            ),
            self._lerp(
                self._grad(p[ab + zi], xf, yf - 1, zf),
                self._grad(p[bb + zi], xf - 1, yf - 1, zf),
                u,
            ),
            v,
        )

        return (result + 1) / 2

    def _fade(self, t: float) -> float:
        """Fade function."""
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, t: float, a: float, b: float) -> float:
        """Linear interpolation."""
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float, z: float) -> float:
        """Gradient function."""
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 8 else z
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


class CameraAnimation:
    """Represents an animation of the camera."""

    def __init__(
        self,
        start_pos: Vec2,
        end_pos: Vec2,
        duration: float,
        ease_type: EaseType = EaseType.LINEAR,
        on_complete: Optional[Callable] = None,
    ):
        """Initialize a camera animation."""
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.duration = duration
        self.elapsed = 0.0
        self.ease_type = ease_type
        self.on_complete = on_complete
        self.finished = False

    def update(self, dt: float) -> Vec2:
        """Update animation and return current position."""
        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.finished = True
            if self.on_complete:
                self.on_complete()
            return self.end_pos

        progress = self.elapsed / self.duration
        easing_func = Easing.get_easing_function(self.ease_type)
        eased_progress = easing_func(progress)

        return self.start_pos.lerp(self.end_pos, eased_progress)


class ZoomAnimation:
    """Represents a zoom animation."""

    def __init__(
        self,
        start_zoom: float,
        end_zoom: float,
        duration: float,
        ease_type: EaseType = EaseType.LINEAR,
        on_complete: Optional[Callable] = None,
    ):
        """Initialize a zoom animation."""
        self.start_zoom = start_zoom
        self.end_zoom = end_zoom
        self.duration = duration
        self.elapsed = 0.0
        self.ease_type = ease_type
        self.on_complete = on_complete
        self.finished = False

    def update(self, dt: float) -> float:
        """Update animation and return current zoom."""
        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.finished = True
            if self.on_complete:
                self.on_complete()
            return self.end_zoom

        progress = self.elapsed / self.duration
        easing_func = Easing.get_easing_function(self.ease_type)
        eased_progress = easing_func(progress)

        return self.start_zoom + (self.end_zoom - self.start_zoom) * eased_progress


class CameraShake:
    """Camera shake effect."""

    def __init__(
        self,
        intensity: float = 5.0,
        duration: float = 0.5,
        frequency: float = 10.0,
    ):
        """Initialize camera shake."""
        self.intensity = intensity
        self.duration = duration
        self.frequency = frequency
        self.elapsed = 0.0
        self.finished = False
        self.perlin = PerlinNoise()

    def update(self, dt: float) -> Vec2:
        """Update shake and return offset."""
        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.finished = True
            return Vec2(0, 0)

        progress = self.elapsed / self.duration
        time_scale = self.frequency

        shake_x = self.perlin.noise(self.elapsed * time_scale) * 2 - 1
        shake_y = self.perlin.noise(self.elapsed * time_scale + 100) * 2 - 1

        fade = 1.0 - progress

        return Vec2(shake_x * self.intensity * fade, shake_y * self.intensity * fade)


class ParallaxLayer:
    """Represents a parallax layer."""

    def __init__(self, depth: float = 0.5):
        """Initialize parallax layer."""
        self.depth = max(0.0, min(1.0, depth))


class CameraFollowMode(Enum):
    """Camera follow modes."""

    NONE = "none"
    LERP = "lerp"
    PREDICT = "predict"
    LEADING = "leading"


class EnhancedCamera:
    """Enhanced camera system with animations, shake, culling, and parallax."""

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 800.0,
        height: float = 600.0,
        angle: float = 0.0,
    ):
        """Initialize enhanced camera."""
        self.position = Vec2(x, y)
        self.width = width
        self.height = height
        self.angle = angle
        self.zoom = 1.0

        # Animation state
        self.animation: Optional[CameraAnimation] = None
        self.zoom_animation: Optional[ZoomAnimation] = None
        self.shake: Optional[CameraShake] = None
        self.shake_offset = Vec2(0, 0)

        # Follow state
        self.follow_target: Optional[Vec2] = None
        self.follow_mode = CameraFollowMode.NONE
        self.follow_speed = 5.0
        self.predict_distance = 50.0
        self.leading_angle = 0.0

        # Bounds
        self.bounds_min: Optional[Vec2] = None
        self.bounds_max: Optional[Vec2] = None

        # Parallax layers
        self.parallax_layers: List[ParallaxLayer] = []

    def get_viewport_rect(self) -> Tuple[float, float, float, float]:
        """Get current viewport as (x, y, width, height)."""
        w = self.width / self.zoom
        h = self.height / self.zoom
        return (self.position.x - w / 2, self.position.y - h / 2, w, h)

    def is_point_visible(self, x: float, y: float) -> bool:
        """Check if a point is visible in viewport."""
        vx, vy, vw, vh = self.get_viewport_rect()
        return vx <= x <= vx + vw and vy <= y <= vy + vh

    def is_rect_visible(self, x: float, y: float, width: float, height: float) -> bool:
        """Check if a rectangle is visible in viewport (AABB culling)."""
        vx, vy, vw, vh = self.get_viewport_rect()

        return not (x + width < vx or x > vx + vw or y + height < vy or y > vy + vh)

    def animate_to(
        self,
        target_pos: Vec2,
        duration: float,
        ease_type: EaseType = EaseType.LINEAR,
        on_complete: Optional[Callable] = None,
    ) -> None:
        """Animate camera to target position."""
        self.animation = CameraAnimation(
            self.position, target_pos, duration, ease_type, on_complete
        )

    def zoom_to(
        self,
        target_zoom: float,
        duration: float,
        ease_type: EaseType = EaseType.LINEAR,
        on_complete: Optional[Callable] = None,
    ) -> None:
        """Animate zoom level."""
        self.zoom_animation = ZoomAnimation(
            self.zoom, target_zoom, duration, ease_type, on_complete
        )

    def apply_shake(
        self,
        intensity: float = 5.0,
        duration: float = 0.5,
        frequency: float = 10.0,
    ) -> None:
        """Apply camera shake effect."""
        self.shake = CameraShake(intensity, duration, frequency)

    def set_follow_target(
        self,
        target: Optional[Vec2],
        mode: CameraFollowMode = CameraFollowMode.LERP,
        speed: float = 5.0,
    ) -> None:
        """Set camera follow target."""
        self.follow_target = target
        self.follow_mode = mode
        self.follow_speed = speed

    def set_bounds(self, min_pos: Vec2, max_pos: Vec2) -> None:
        """Set camera bounds to clamp position."""
        self.bounds_min = min_pos
        self.bounds_max = max_pos

    def add_parallax_layer(self, depth: float) -> ParallaxLayer:
        """Add a parallax layer."""
        layer = ParallaxLayer(depth)
        self.parallax_layers.append(layer)
        return layer

    def get_parallax_offset(self, layer_depth: float) -> Vec2:
        """Get parallax offset for a layer."""
        return self.position * (1.0 - layer_depth)

    def _update_follow(self, dt: float) -> None:
        """Update camera following."""
        if not self.follow_target or self.follow_mode == CameraFollowMode.NONE:
            return

        if self.follow_mode == CameraFollowMode.LERP:
            direction = self.follow_target - self.position
            distance = direction.distance_to(Vec2(0, 0))

            if distance > 0.1:
                move_distance = min(self.follow_speed * dt, distance)
                move_direction = Vec2(
                    direction.x / distance * move_distance,
                    direction.y / distance * move_distance,
                )
                self.position = self.position + move_direction

        elif self.follow_mode == CameraFollowMode.PREDICT:
            direction = self.follow_target - self.position
            predicted_target = self.follow_target + direction * self.predict_distance
            direction = predicted_target - self.position
            distance = direction.distance_to(Vec2(0, 0))

            if distance > 0.1:
                move_distance = min(self.follow_speed * dt, distance)
                move_direction = Vec2(
                    direction.x / distance * move_distance,
                    direction.y / distance * move_distance,
                )
                self.position = self.position + move_direction

        elif self.follow_mode == CameraFollowMode.LEADING:
            direction = self.follow_target - self.position
            distance = direction.distance_to(Vec2(0, 0))

            if distance > 0.1:
                lead_offset = Vec2(
                    math.cos(self.leading_angle) * self.predict_distance,
                    math.sin(self.leading_angle) * self.predict_distance,
                )
                target = self.follow_target + lead_offset

                direction = target - self.position
                distance = direction.distance_to(Vec2(0, 0))
                move_distance = min(self.follow_speed * dt, distance)
                move_direction = Vec2(
                    direction.x / distance * move_distance,
                    direction.y / distance * move_distance,
                )
                self.position = self.position + move_direction

        self._apply_bounds()

    def _apply_bounds(self) -> None:
        """Apply position bounds."""
        if self.bounds_min and self.bounds_max:
            half_w = (self.width / self.zoom) / 2
            half_h = (self.height / self.zoom) / 2

            self.position.x = max(
                self.bounds_min.x + half_w,
                min(self.position.x, self.bounds_max.x - half_w),
            )
            self.position.y = max(
                self.bounds_min.y + half_h,
                min(self.position.y, self.bounds_max.y - half_h),
            )

    def update(self, dt: float) -> None:
        """Update camera state."""
        if self.animation and not self.animation.finished:
            self.position = self.animation.update(dt)

        if self.zoom_animation and not self.zoom_animation.finished:
            self.zoom = self.zoom_animation.update(dt)

        if self.shake and not self.shake.finished:
            self.shake_offset = self.shake.update(dt)

        self._update_follow(dt)

    def set_position(self, x: float, y: float) -> None:
        """Set camera position."""
        self.position = Vec2(x, y)
        self._apply_bounds()

    def set_angle(self, angle: float) -> None:
        """Set camera angle in degrees."""
        self.angle = angle % 360

    def set_zoom(self, zoom: float) -> None:
        """Set zoom level."""
        self.zoom = max(0.1, zoom)

    def get_world_position(self, screen_x: float, screen_y: float) -> Vec2:
        """Convert screen coordinates to world coordinates."""
        world_x = screen_x / self.zoom
        world_y = screen_y / self.zoom

        vx, vy, _, _ = self.get_viewport_rect()
        world_x += vx
        world_y += vy

        return Vec2(world_x, world_y)

    def get_screen_position(self, world_x: float, world_y: float) -> Vec2:
        """Convert world coordinates to screen coordinates."""
        vx, vy, _, _ = self.get_viewport_rect()
        screen_x = (world_x - vx) * self.zoom
        screen_y = (world_y - vy) * self.zoom

        return Vec2(screen_x, screen_y)
