"""
Interactive Camera System Test & Demo

Demonstrates enhanced camera features:
- Camera animations with easing
- Camera shake effects
- Viewport culling
- Parallax layer system
- Camera follow modes (Lerp, Predict, Leading)
- Camera zoom animations
- Camera bounds

Controls:
  MOUSE: Click to animate camera to position
  W/A/S/D: Manual camera movement
  Q/E: Zoom in/out
  SPACE: Apply camera shake
  1/2/3: Switch follow modes (Lerp/Predict/Leading)
  T: Toggle follow target
  P: Toggle parallax visualization
  C: Toggle viewport culling visualization
  H: Toggle help
  ESC: Exit demo
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
import math
from sweet.camera import (
    EnhancedCamera,
    Vec2,
    EaseType,
    CameraFollowMode,
    Easing,
    CameraAnimation,
    ZoomAnimation,
    CameraShake,
    ParallaxLayer,
)


class CameraDemo:
    """Interactive camera system demonstration."""

    def __init__(self):
        """Initialize the demo application."""
        pygame.init()
        self.screen_width = 1280
        self.screen_height = 960
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Sweet Engine - Camera System Demo")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 18)
        self.running = True

        # Create enhanced camera
        self.camera = EnhancedCamera(
            x=400,
            y=300,
            width=self.screen_width,
            height=self.screen_height,
        )

        # World entities
        self.world_objects = self._create_world_objects()

        # Follow target (moving around)        self.follow_target = Vec2(400, 300)
        self.follow_enabled = False
        self.follow_mode = CameraFollowMode.LERP

        # Visualization toggles
        self.show_help = True
        self.show_culling = False
        self.show_parallax = True
        self.show_viewport = True

        # Demo state
        self.time = 0.0

    def _create_world_objects(self) -> list:
        """Create world objects to visualize."""
        objects = []

        # Create a grid of objects
        for x in range(0, 2000, 100):
            for y in range(0, 1500, 100):
                objects.append(
                    {
                        "x": x,
                        "y": y,
                        "width": 80,
                        "height": 80,
                        "color": (100 + (x % 100), 100 + (y % 100), 150),
                        "label": f"({x}, {y})",
                    }
                )

        # Add some moving objects
        for i in range(5):
            objects.append(
                {
                    "x": 300 + i * 200,
                    "y": 400,
                    "width": 50,
                    "height": 50,
                    "color": (255, 150, 100),
                    "label": f"Dynamic {i}",
                    "moving": True,
                    "angle": i * 72,
                }
            )

        return objects

    def handle_input(self) -> None:
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_h:
                    self.show_help = not self.show_help
                elif event.key == pygame.K_c:
                    self.show_culling = not self.show_culling
                elif event.key == pygame.K_p:
                    self.show_parallax = not self.show_parallax
                elif event.key == pygame.K_SPACE:
                    # Apply camera shake
                    self.camera.apply_shake(
                        intensity=10.0, duration=0.5, frequency=15.0
                    )
                elif event.key == pygame.K_q:
                    # Zoom in
                    self.camera.zoom_to(
                        2.0, duration=0.5, ease_type=EaseType.EASE_OUT_QUAD
                    )
                elif event.key == pygame.K_e:
                    # Zoom out
                    self.camera.zoom_to(
                        0.5, duration=0.5, ease_type=EaseType.EASE_OUT_QUAD
                    )
                elif event.key == pygame.K_1:
                    # Lerp follow mode
                    self.follow_mode = CameraFollowMode.LERP
                elif event.key == pygame.K_2:
                    # Predict follow mode
                    self.follow_mode = CameraFollowMode.PREDICT
                elif event.key == pygame.K_3:
                    # Leading follow mode
                    self.follow_mode = CameraFollowMode.LEADING
                elif event.key == pygame.K_t:
                    # Toggle follow
                    self.follow_enabled = not self.follow_enabled
                    if self.follow_enabled:
                        self.camera.set_follow_target(
                            self.follow_target, self.follow_mode, speed=150.0
                        )
                    else:
                        self.camera.set_follow_target(None)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Convert screen to world position and animate camera there
                    world_pos = self.camera.get_world_position(
                        event.pos[0], event.pos[1]
                    )
                    self.camera.animate_to(
                        world_pos, duration=1.5, ease_type=EaseType.EASE_IN_OUT_CUBIC
                    )

        # Keyboard continuous input
        keys = pygame.key.get_pressed()
        speed = 200

        if keys[pygame.K_w]:
            self.camera.position.y -= speed * (self.clock.get_time() / 1000.0)
        if keys[pygame.K_s]:
            self.camera.position.y += speed * (self.clock.get_time() / 1000.0)
        if keys[pygame.K_a]:
            self.camera.position.x -= speed * (self.clock.get_time() / 1000.0)
        if keys[pygame.K_d]:
            self.camera.position.x += speed * (self.clock.get_time() / 1000.0)

    def update(self, dt: float) -> None:
        """Update game state."""
        self.time += dt
        self.camera.update(dt)

        # Update follow target (move in circle)
        if self.follow_enabled:
            angle = self.time * 0.5
            self.follow_target.x = 1000 + math.cos(angle) * 400
            self.follow_target.y = 750 + math.sin(angle) * 300
            self.camera.set_follow_target(
                self.follow_target, self.follow_mode, speed=150.0
            )

        # Update moving objects
        for obj in self.world_objects:
            if obj.get("moving"):
                angle = obj["angle"] + self.time * 1.0
                obj["x"] = 400 + math.cos(angle) * 200
                obj["y"] = 400 + math.sin(angle) * 150

    def draw(self) -> None:
        """Draw everything."""
        self.screen.fill((20, 20, 30))

        # Draw world background
        self._draw_world_background()

        # Draw world objects
        self._draw_world_objects()

        # Draw follow target if enabled
        if self.follow_enabled:
            self._draw_follow_target()

        # Draw viewport culling info if enabled
        if self.show_culling:
            self._draw_culling_info()

        # Draw parallax visualization if enabled
        if self.show_parallax:
            self._draw_parallax_info()

        # Draw camera viewport indicator
        self._draw_viewport_indicator()

        # Draw HUD
        self._draw_hud()

        # Draw help if enabled
        if self.show_help:
            self._draw_help()

        pygame.display.flip()

    def _draw_world_background(self) -> None:
        """Draw world background grid."""
        vx, vy, vw, vh = self.camera.get_viewport_rect()

        # Draw grid
        grid_size = 100
        start_x = int(vx - (vx % grid_size))
        start_y = int(vy - (vy % grid_size))

        for x in range(start_x, int(vx + vw), grid_size):
            screen_x = (x - vx) * self.camera.zoom
            pygame.draw.line(
                self.screen, (40, 40, 50), (screen_x, 0), (screen_x, self.screen_height)
            )

        for y in range(start_y, int(vy + vh), grid_size):
            screen_y = (y - vy) * self.camera.zoom
            pygame.draw.line(
                self.screen, (40, 40, 50), (0, screen_y), (self.screen_width, screen_y)
            )

    def _draw_world_objects(self) -> None:
        """Draw world objects."""
        drawn = 0
        culled = 0

        for obj in self.world_objects:
            # Check visibility with viewport culling
            if self.camera.is_rect_visible(
                obj["x"], obj["y"], obj["width"], obj["height"]
            ):
                self._draw_object(obj)
                drawn += 1
            else:
                culled += 1

        # Store for HUD
        self.drawn_objects = drawn
        self.culled_objects = culled

    def _draw_object(self, obj: dict) -> None:
        """Draw a single object."""
        vx, vy, _, _ = self.camera.get_viewport_rect()

        screen_x = (obj["x"] - vx) * self.camera.zoom
        screen_y = (obj["y"] - vy) * self.camera.zoom
        width = obj["width"] * self.camera.zoom
        height = obj["height"] * self.camera.zoom

        pygame.draw.rect(self.screen, obj["color"], (screen_x, screen_y, width, height))
        pygame.draw.rect(
            self.screen, (200, 200, 200), (screen_x, screen_y, width, height), 2
        )

    def _draw_follow_target(self) -> None:
        """Draw the follow target."""
        vx, vy, _, _ = self.camera.get_viewport_rect()

        screen_x = (self.follow_target.x - vx) * self.camera.zoom
        screen_y = (self.follow_target.y - vy) * self.camera.zoom

        pygame.draw.circle(
            self.screen, (255, 200, 100), (int(screen_x), int(screen_y)), 15
        )
        pygame.draw.circle(
            self.screen, (255, 255, 100), (int(screen_x), int(screen_y)), 15, 3
        )

    def _draw_culling_info(self) -> None:
        """Draw viewport culling visualization."""
        vx, vy, vw, vh = self.camera.get_viewport_rect()

        # Draw viewport bounds
        corners = [
            (vx, vy),
            (vx + vw, vy),
            (vx + vw, vy + vh),
            (vx, vy + vh),
        ]

        screen_corners = []
        for cx, cy in corners:
            screen_x = (cx - vx) * self.camera.zoom
            screen_y = (cy - vy) * self.camera.zoom
            screen_corners.append((screen_x, screen_y))

        pygame.draw.polygon(self.screen, (100, 255, 100), screen_corners, 3)

    def _draw_parallax_info(self) -> None:
        """Draw parallax layer information."""
        for i, depth in enumerate([0.0, 0.3, 0.6, 0.9]):
            offset = self.camera.get_parallax_offset(depth)
            text = self.small_font.render(
                f"Layer {i} (depth={depth})", True, (100, 200, 255)
            )
            self.screen.blit(text, (10, 300 + i * 25))

    def _draw_viewport_indicator(self) -> None:
        """Draw a viewport indicator rectangle."""
        vx, vy, _, _ = self.camera.get_viewport_rect()
        pygame.draw.rect(
            self.screen,
            (100, 255, 100),
            (0, 0, self.screen_width, self.screen_height),
            3,
        )

    def _draw_hud(self) -> None:
        """Draw heads-up display."""
        hud_items = [
            f"Camera Pos: ({self.camera.position.x:.1f}, {self.camera.position.y:.1f})",
            f"Zoom: {self.camera.zoom:.2f}x",
            f"Viewport: {self.camera.get_viewport_rect()}",
            f"Drawn: {getattr(self, 'drawn_objects', 0)} | Culled: {getattr(self, 'culled_objects', 0)}",
            f"Follow: {'ON (' + self.follow_mode.value + ')' if self.follow_enabled else 'OFF'}",
            f"FPS: {self.clock.get_fps():.1f}",
        ]

        for i, item in enumerate(hud_items):
            text = self.small_font.render(item, True, (150, 200, 150))
            self.screen.blit(text, (10, 10 + i * 25))

    def _draw_help(self) -> None:
        """Draw help text."""
        help_items = [
            "MOUSE: Click to animate camera to position",
            "W/A/S/D: Manual camera movement",
            "Q/E: Zoom in/out",
            "SPACE: Apply camera shake",
            "1/2/3: Switch follow modes (Lerp/Predict/Leading)",
            "T: Toggle follow target",
            "P: Toggle parallax visualization",
            "C: Toggle viewport culling visualization",
            "H: Toggle help",
        ]

        help_y = self.screen_height - len(help_items) * 25 - 20
        for i, item in enumerate(help_items):
            text = self.small_font.render(item, True, (100, 150, 200))
            self.screen.blit(text, (10, help_y + i * 25))

    def run(self) -> None:
        """Run the demo application."""
        print(__doc__)
        print("\nStarting Camera System Demo...")

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_input()
            self.update(dt)
            self.draw()

        pygame.quit()
        print("Camera Demo closed.")


def main():
    """Entry point for the camera demo."""
    try:
        app = CameraDemo()
        app.run()
    except Exception as e:
        print(f"Error running demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
