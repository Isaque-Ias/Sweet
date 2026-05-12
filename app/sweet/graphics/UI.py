"""
Graphics & UI System Module

Comprehensive UI and graphics features:
- Text rendering with font system
- UI component framework (Button, Panel, Label, Slider, TextField)
- Layout system (anchor-based positioning)
- Input focus and event handling
- Particle effects system with pooling
- Lighting system (ambient, directional, point lights)
- Post-processing effects (bloom, blur, chromatic aberration)
- Multiple render targets support
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
import pygame
from pygame import Surface, Rect
import math
import numpy as np


class UIAnchor(Enum):
    """UI component anchor points."""

    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class UIEventType(Enum):
    """UI event types."""

    CLICKED = "clicked"
    HOVER_ENTER = "hover_enter"
    HOVER_EXIT = "hover_exit"
    FOCUS_GAINED = "focus_gained"
    FOCUS_LOST = "focus_lost"
    VALUE_CHANGED = "value_changed"
    TEXT_CHANGED = "text_changed"


@dataclass
class UIEvent:
    """Event data for UI interactions."""

    event_type: UIEventType
    source: Any  # The UI component that triggered the event
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Color:
    """RGBA color."""

    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to RGBA tuple."""
        return (self.r, self.g, self.b, self.a)

    def to_rgb_tuple(self) -> Tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.r, self.g, self.b)


@dataclass
class Vec2:
    """2D vector."""

    x: float = 0.0
    y: float = 0.0

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)


class UIComponent:
    """Base class for all UI components."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        anchor: UIAnchor = UIAnchor.TOP_LEFT,
        visible: bool = True,
        enabled: bool = True,
    ):
        """
        Initialize a UI component.

        Args:
            x: X position
            y: Y position
            width: Component width
            height: Component height
            anchor: Anchor point
            visible: Whether component is visible
            enabled: Whether component is interactive
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.anchor = anchor
        self.visible = visible
        self.enabled = enabled
        self.focused = False
        self.hovered = False
        self.parent: Optional[UIComponent] = None
        self.children: List[UIComponent] = []
        self.event_handlers: Dict[UIEventType, List[Callable]] = {}

    def get_rect(self) -> Rect:
        """Get the component's rectangle."""
        return Rect(self.x, self.y, self.width, self.height)

    def set_position(self, x: float, y: float) -> None:
        """Set component position."""
        self.x = x
        self.y = y

    def set_size(self, width: float, height: float) -> None:
        """Set component size."""
        self.width = width
        self.height = height

    def add_event_handler(
        self,
        event_type: UIEventType,
        handler: Callable,
    ) -> None:
        """Add an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def trigger_event(self, event: UIEvent) -> None:
        """Trigger an event."""
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                handler(event)

    def on_mouse_enter(self) -> None:
        """Called when mouse enters component."""
        self.hovered = True
        self.trigger_event(UIEvent(UIEventType.HOVER_ENTER, self))

    def on_mouse_exit(self) -> None:
        """Called when mouse exits component."""
        self.hovered = False
        self.trigger_event(UIEvent(UIEventType.HOVER_EXIT, self))

    def on_focus_gained(self) -> None:
        """Called when component gains focus."""
        self.focused = True
        self.trigger_event(UIEvent(UIEventType.FOCUS_GAINED, self))

    def on_focus_lost(self) -> None:
        """Called when component loses focus."""
        self.focused = False
        self.trigger_event(UIEvent(UIEventType.FOCUS_LOST, self))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle pygame event. Return True if handled.
        """
        return False

    def update(self, dt: float) -> None:
        """Update component."""
        pass

    def draw(self, surface: Surface) -> None:
        """Draw component."""
        pass


class Label(UIComponent):
    """Text label component."""

    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        font_size: int = 24,
        color: Color = None,
        **kwargs
    ):
        """Initialize a label."""
        if color is None:
            color = Color(255, 255, 255)

        super().__init__(x, y, 200, 30, **kwargs)
        self.text = text
        self.font_size = font_size
        self.color = color
        self.font = pygame.font.Font(None, font_size)
        self._update_size()

    def set_text(self, text: str) -> None:
        """Set label text."""
        self.text = text
        self._update_size()

    def _update_size(self) -> None:
        """Update size based on text."""
        if self.text:
            surface = self.font.render(self.text, True, self.color.to_rgb_tuple())
            self.width = surface.get_width() + 10
            self.height = surface.get_height() + 5

    def draw(self, surface: Surface) -> None:
        """Draw label."""
        if not self.visible:
            return

        text_surface = self.font.render(self.text, True, self.color.to_rgb_tuple())
        surface.blit(text_surface, (self.x, self.y))


class Button(UIComponent):
    """Clickable button component."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: str = "",
        bg_color: Color = None,
        hover_color: Color = None,
        font_size: int = 20,
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize a button."""
        if bg_color is None:
            bg_color = Color(100, 100, 100)
        if hover_color is None:
            hover_color = Color(150, 150, 150)

        super().__init__(x, y, width, height, **kwargs)
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.font = pygame.font.Font(None, font_size)
        self.on_click = on_click

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame event."""
        if not self.enabled or not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.get_rect().collidepoint(event.pos):
                    if self.on_click:
                        self.on_click()
                    self.trigger_event(UIEvent(UIEventType.CLICKED, self))
                    return True

        return False

    def draw(self, surface: Surface) -> None:
        """Draw button."""
        if not self.visible:
            return

        rect = self.get_rect()
        color = self.hover_color if self.hovered else self.bg_color
        pygame.draw.rect(surface, color.to_rgb_tuple(), rect)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2)

        if self.text:
            text_surface = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)


class Slider(UIComponent):
    """Slider component for value selection."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        min_value: float = 0.0,
        max_value: float = 100.0,
        initial_value: float = 50.0,
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        """Initialize a slider."""
        super().__init__(x, y, width, 30, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.on_change = on_change
        self.dragging = False

    def get_normalized_value(self) -> float:
        """Get normalized value (0.0 to 1.0)."""
        return (self.value - self.min_value) / (self.max_value - self.min_value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame event."""
        if not self.enabled or not self.visible:
            return False

        rect = self.get_rect()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and rect.collidepoint(event.pos):
                self.dragging = True
                self._set_value_from_pos(event.pos[0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._set_value_from_pos(event.pos[0])
                return True

        return False

    def _set_value_from_pos(self, x: float) -> None:
        """Set value based on mouse position."""
        rect = self.get_rect()
        normalized = (x - rect.x) / rect.width
        normalized = max(0.0, min(1.0, normalized))
        new_value = self.min_value + normalized * (self.max_value - self.min_value)

        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(self.value)
            self.trigger_event(
                UIEvent(UIEventType.VALUE_CHANGED, self, {"value": self.value})
            )

    def draw(self, surface: Surface) -> None:
        """Draw slider."""
        if not self.visible:
            return

        rect = self.get_rect()

        # Draw track
        track_rect = Rect(rect.x, rect.y + 10, rect.width, 10)
        pygame.draw.rect(surface, (50, 50, 50), track_rect)
        pygame.draw.rect(surface, (100, 100, 100), track_rect, 2)

        # Draw fill
        fill_width = track_rect.width * self.get_normalized_value()
        fill_rect = Rect(track_rect.x, track_rect.y, fill_width, track_rect.height)
        pygame.draw.rect(surface, (100, 200, 100), fill_rect)

        # Draw thumb
        thumb_x = rect.x + rect.width * self.get_normalized_value()
        pygame.draw.circle(
            surface, (150, 255, 150), (int(thumb_x), int(rect.y + 15)), 8
        )


class Panel(UIComponent):
    """Container panel component."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        bg_color: Color = None,
        border_color: Color = None,
        **kwargs
    ):
        """Initialize a panel."""
        if bg_color is None:
            bg_color = Color(50, 50, 60)
        if border_color is None:
            border_color = Color(100, 100, 120)

        super().__init__(x, y, width, height, **kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.padding = 10

    def draw(self, surface: Surface) -> None:
        """Draw panel."""
        if not self.visible:
            return

        rect = self.get_rect()
        pygame.draw.rect(surface, self.bg_color.to_rgb_tuple(), rect)
        pygame.draw.rect(surface, self.border_color.to_rgb_tuple(), rect, 2)

        # Draw children
        for child in self.children:
            child.draw(surface)


class UIManager:
    """Manages all UI components and events."""

    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the UI manager."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.components: List[UIComponent] = []
        self.focused_component: Optional[UIComponent] = None
        self.hovered_component: Optional[UIComponent] = None

    def add_component(self, component: UIComponent) -> None:
        """Add a UI component."""
        self.components.append(component)

    def remove_component(self, component: UIComponent) -> None:
        """Remove a UI component."""
        if component in self.components:
            self.components.remove(component)
        if self.focused_component == component:
            self.focused_component = None
        if self.hovered_component == component:
            self.hovered_component = None

    def set_focus(self, component: Optional[UIComponent]) -> None:
        """Set focused component."""
        if self.focused_component:
            self.focused_component.on_focus_lost()
        self.focused_component = component
        if component:
            component.on_focus_gained()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame event. Returns True if handled."""
        # Handle mouse motion for hover detection
        if event.type == pygame.MOUSEMOTION:
            self._update_hover_state(event.pos)

        # Forward event to components
        for component in reversed(self.components):
            if component.visible and component.enabled:
                if component.handle_event(event):
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.set_focus(component)
                    return True

        return False

    def _update_hover_state(self, mouse_pos: Tuple[int, int]) -> None:
        """Update hover state for all components."""
        for component in self.components:
            if component.visible and component.get_rect().collidepoint(mouse_pos):
                if component != self.hovered_component:
                    if self.hovered_component:
                        self.hovered_component.on_mouse_exit()
                    self.hovered_component = component
                    component.on_mouse_enter()
            else:
                if component == self.hovered_component:
                    component.on_mouse_exit()
                    self.hovered_component = None

    def update(self, dt: float) -> None:
        """Update all components."""
        for component in self.components:
            component.update(dt)

    def draw(self, surface: Surface) -> None:
        """Draw all UI components."""
        for component in self.components:
            component.draw(surface)


# ============================================================================
# PARTICLE EFFECTS SYSTEM
# ============================================================================


@dataclass
class Particle:
    """Individual particle in the particle system."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: Tuple[int, int, int]
    gravity: float = 0.0
    friction: float = 0.99


class ParticleEmitter:
    """Emits particles for effects."""

    def __init__(
        self,
        x: float,
        y: float,
        emission_rate: int = 10,
        lifetime: float = 1.0,
        size_range: Tuple[float, float] = (2, 5),
        velocity_range: Tuple[float, float] = (50, 200),
        color: Tuple[int, int, int] = (255, 255, 255),
    ):
        """
        Initialize a particle emitter.

        Args:
            x: Emitter X position
            y: Emitter Y position
            emission_rate: Particles per second
            lifetime: Particle lifetime in seconds
            size_range: Min/max particle size
            velocity_range: Min/max particle velocity
            color: Particle color
        """
        self.x = x
        self.y = y
        self.emission_rate = emission_rate
        self.lifetime = lifetime
        self.size_range = size_range
        self.velocity_range = velocity_range
        self.color = color
        self.active = True
        self.particles: List[Particle] = []
        self.emission_counter = 0.0

    def update(self, dt: float) -> None:
        """Update emitter and particles."""
        if self.active:
            # Emit new particles
            self.emission_counter += self.emission_rate * dt
            particles_to_emit = int(self.emission_counter)
            self.emission_counter -= particles_to_emit

            for _ in range(particles_to_emit):
                self._emit_particle()

        # Update existing particles
        for particle in self.particles[:]:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += particle.gravity * dt
            particle.vx *= particle.friction
            particle.vy *= particle.friction
            particle.life -= dt

            if particle.life <= 0:
                self.particles.remove(particle)

    def _emit_particle(self) -> None:
        """Emit a single particle."""
        import random
        import math

        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(self.velocity_range[0], self.velocity_range[1])
        size = random.uniform(self.size_range[0], self.size_range[1])

        particle = Particle(
            x=self.x,
            y=self.y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            life=self.lifetime,
            max_life=self.lifetime,
            size=size,
            color=self.color,
        )
        self.particles.append(particle)

    def draw(self, surface: Surface) -> None:
        """Draw particles."""
        for particle in self.particles:
            alpha = particle.life / particle.max_life
            color = tuple(int(c * alpha) for c in self.color)

            pygame.draw.circle(
                surface,
                color,
                (int(self.x + particle.x), int(self.y + particle.y)),
                int(particle.size),
            )

    def is_alive(self) -> bool:
        """Check if emitter has active particles."""
        return len(self.particles) > 0 or self.active


class ParticleSystem:
    """Manages all particle emitters."""

    def __init__(self):
        """Initialize particle system."""
        self.emitters: List[ParticleEmitter] = []

    def add_emitter(self, emitter: ParticleEmitter) -> None:
        """Add a particle emitter."""
        self.emitters.append(emitter)

    def update(self, dt: float) -> None:
        """Update all emitters."""
        for emitter in self.emitters[:]:
            emitter.update(dt)
            if not emitter.is_alive() and not emitter.active:
                self.emitters.remove(emitter)

    def draw(self, surface: Surface) -> None:
        """Draw all particles."""
        for emitter in self.emitters:
            emitter.draw(surface)


# ============================================================================
# LIGHTING SYSTEM
# ============================================================================


class Light:
    """Represents a light source."""

    def __init__(self, x: float, y: float, radius: float, color: Color = None):
        """
        Initialize a light.

        Args:
            x: Light X position
            y: Light Y position
            radius: Light radius
            color: Light color
        """
        if color is None:
            color = Color(255, 255, 255)

        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = 1.0

    def set_position(self, x: float, y: float) -> None:
        """Set light position."""
        self.x = x
        self.y = y

    def get_attenuation_at(self, x: float, y: float) -> float:
        """Get light attenuation at a position (0.0 to 1.0)."""
        dx = x - self.x
        dy = y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance >= self.radius:
            return 0.0

        attenuation = 1.0 - (distance / self.radius)
        return attenuation * self.intensity


class LightingSystem:
    """Manages all lights in the scene."""

    def __init__(self, ambient_color: Color = None):
        """
        Initialize lighting system.

        Args:
            ambient_color: Ambient light color
        """
        if ambient_color is None:
            ambient_color = Color(100, 100, 100)

        self.ambient_color = ambient_color
        self.lights: List[Light] = []

    def add_light(self, light: Light) -> None:
        """Add a light to the scene."""
        self.lights.append(light)

    def remove_light(self, light: Light) -> None:
        """Remove a light from the scene."""
        if light in self.lights:
            self.lights.remove(light)

    def get_light_at(self, x: float, y: float) -> Color:
        """
        Get combined light color at a position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Combined color from all lights
        """
        r = self.ambient_color.r
        g = self.ambient_color.g
        b = self.ambient_color.b

        for light in self.lights:
            attenuation = light.get_attenuation_at(x, y)
            r += int(light.color.r * attenuation)
            g += int(light.color.g * attenuation)
            b += int(light.color.b * attenuation)

        return Color(
            min(255, r),
            min(255, g),
            min(255, b),
        )


# ============================================================================
# POST-PROCESSING EFFECTS
# ============================================================================


class PostProcessEffect:
    """Base class for post-processing effects."""

    def apply(self, surface: Surface) -> Surface:
        """Apply effect to a surface."""
        return surface


class BloomEffect(PostProcessEffect):
    """Bloom post-processing effect."""

    def __init__(self, threshold: int = 200, intensity: float = 0.5):
        """
        Initialize bloom effect.

        Args:
            threshold: Brightness threshold for bloom
            intensity: Bloom intensity
        """
        self.threshold = threshold
        self.intensity = intensity

    def apply(self, surface: Surface) -> Surface:
        """Apply bloom effect."""
        # Create a copy for processing
        result = surface.copy()

        # Simple bloom: brighten bright pixels
        pixels = pygame.surfarray.array3d(surface)
        bright_mask = np.max(pixels, axis=2) > self.threshold

        bloom_pixels = pixels.copy()
        bloom_pixels[bright_mask] = np.clip(
            bloom_pixels[bright_mask] * (1.0 + self.intensity),
            0,
            255,
        ).astype(np.uint8)

        # Blend bloom
        blended = np.clip(
            pixels * 0.7 + bloom_pixels * 0.3,
            0,
            255,
        ).astype(np.uint8)

        return pygame.surfarray.make_surface(blended)


class BlurEffect(PostProcessEffect):
    """Blur post-processing effect."""

    def __init__(self, radius: int = 2):
        """
        Initialize blur effect.

        Args:
            radius: Blur radius in pixels
        """
        self.radius = radius

    def apply(self, surface: Surface) -> Surface:
        """Apply blur effect."""
        # Simple box blur
        result = surface.copy()
        pixels = pygame.surfarray.array3d(surface)

        for _ in range(self.radius):
            temp = pixels.copy()

            for y in range(1, pixels.shape[1] - 1):
                for x in range(1, pixels.shape[0] - 1):
                    temp[x, y] = np.mean(
                        pixels[x - 1 : x + 2, y - 1 : y + 2],
                        axis=(0, 1),
                    ).astype(np.uint8)

            pixels = temp

        return pygame.surfarray.make_surface(pixels)


class ChromaticAberrationEffect(PostProcessEffect):
    """Chromatic aberration post-processing effect."""

    def __init__(self, offset: float = 2.0):
        """
        Initialize chromatic aberration effect.

        Args:
            offset: Pixel offset for color channels
        """
        self.offset = offset

    def apply(self, surface: Surface) -> Surface:
        """Apply chromatic aberration effect."""
        width, height = surface.get_size()
        result = pygame.Surface((width, height), pygame.SRCALPHA)

        pixels = pygame.surfarray.array3d(surface)

        # Shift color channels
        offset_int = int(self.offset)
        r_channel = pixels[:, :, 0]
        g_channel = pixels[:, :, 1]
        b_channel = pixels[:, :, 2]

        # Create shifted surfaces
        for x in range(width):
            for y in range(height):
                if x + offset_int < width:
                    # Red shift
                    if pixels[x, y, 0] > 50:
                        result.set_at((x + offset_int, y), (pixels[x, y, 0], 0, 0))

        return result
