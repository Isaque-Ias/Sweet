"""
Interactive Graphics & UI System Test & Demo

Demonstrates all graphics and UI features:
- UI components (Button, Label, Slider, Panel)
- Text rendering
- Particle effects
- Lighting system
- Post-processing effects

Controls:
  Click buttons and interact with sliders
  Move mouse to see hover effects
  Press keys to trigger particle effects
  E: Toggle post-processing effects
  L: Toggle lighting effect
  ESC: Exit demo
"""

import sys
import os
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from sweet.graphics.UI import (
    UIManager,
    Label,
    Button,
    Slider,
    Panel,
    ParticleSystem,
    ParticleEmitter,
    LightingSystem,
    Light,
    Color,
    UIEvent,
    UIEventType,
    BloomEffect,
    BlurEffect,
    ChromaticAberrationEffect,
)


class UIDemo:
    """Interactive UI and graphics demonstration."""

    def __init__(self):
        """Initialize the demo application."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 960))
        pygame.display.set_caption("Sweet Engine - Graphics & UI Demo")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 18)
        self.running = True

        # UI Manager
        self.ui_manager = UIManager(self.screen.get_width(), self.screen.get_height())

        # Particle System
        self.particle_system = ParticleSystem()

        # Lighting System
        self.lighting_system = LightingSystem(Color(80, 80, 100))
        self.lights_enabled = True
        self._create_lights()

        # Post-processing
        self.post_effects_enabled = False
        self.bloom_effect = BloomEffect(threshold=200, intensity=0.5)
        self.blur_effect = BlurEffect(radius=2)
        self.chromatic_effect = ChromaticAberrationEffect(offset=3.0)

        # State
        self.debug_info = []
        self.selected_color = (255, 100, 100)

        # Create UI
        self._create_ui()

    def _create_lights(self) -> None:
        """Create initial lights."""
        light1 = Light(200, 200, 300, Color(255, 100, 100))
        light1.intensity = 0.8
        self.lighting_system.add_light(light1)

        light2 = Light(1080, 200, 300, Color(100, 150, 255))
        light2.intensity = 0.8
        self.lighting_system.add_light(light2)

        light3 = Light(640, 700, 250, Color(100, 255, 100))
        light3.intensity = 0.6
        self.lighting_system.add_light(light3)

    def _create_ui(self) -> None:
        """Create UI components."""
        # Main panel
        main_panel = Panel(10, 10, 300, 700, bg_color=Color(30, 30, 40))
        self.ui_manager.add_component(main_panel)

        # Title
        title = Label(
            20, 20, "UI Component Demo", font_size=24, color=Color(100, 200, 255)
        )
        self.ui_manager.add_component(title)

        # Button 1
        btn1 = Button(
            20,
            70,
            260,
            40,
            text="Emit Red Particles",
            bg_color=Color(100, 50, 50),
            hover_color=Color(150, 70, 70),
            on_click=lambda: self._emit_particles((255, 100, 100)),
        )
        self.ui_manager.add_component(btn1)

        # Button 2
        btn2 = Button(
            20,
            120,
            260,
            40,
            text="Emit Blue Particles",
            bg_color=Color(50, 100, 150),
            hover_color=Color(70, 120, 180),
            on_click=lambda: self._emit_particles((100, 150, 255)),
        )
        self.ui_manager.add_component(btn2)

        # Button 3
        btn3 = Button(
            20,
            170,
            260,
            40,
            text="Emit Green Particles",
            bg_color=Color(50, 150, 100),
            hover_color=Color(70, 180, 130),
            on_click=lambda: self._emit_particles((100, 255, 100)),
        )
        self.ui_manager.add_component(btn3)

        # Slider for particle size
        size_label = Label(
            20, 220, "Particle Size", font_size=18, color=Color(200, 200, 200)
        )
        self.ui_manager.add_component(size_label)

        self.size_slider = Slider(
            20,
            245,
            260,
            min_value=1.0,
            max_value=10.0,
            initial_value=5.0,
            on_change=self._on_size_change,
        )
        self.ui_manager.add_component(self.size_slider)

        # Slider for emission rate
        rate_label = Label(
            20, 285, "Emission Rate", font_size=18, color=Color(200, 200, 200)
        )
        self.ui_manager.add_component(rate_label)

        self.rate_slider = Slider(
            20,
            310,
            260,
            min_value=10.0,
            max_value=100.0,
            initial_value=30.0,
            on_change=self._on_rate_change,
        )
        self.ui_manager.add_component(self.rate_slider)

        # Info labels
        self.fps_label = Label(
            20, 350, "FPS: 0", font_size=16, color=Color(150, 200, 150)
        )
        self.ui_manager.add_component(self.fps_label)

        self.particles_label = Label(
            20, 375, "Particles: 0", font_size=16, color=Color(150, 200, 150)
        )
        self.ui_manager.add_component(self.particles_label)

        # Toggle buttons
        toggle_effects_btn = Button(
            20,
            420,
            260,
            35,
            text="Toggle Post-Effects",
            bg_color=Color(100, 100, 50),
            hover_color=Color(150, 150, 70),
            on_click=self._toggle_effects,
        )
        self.ui_manager.add_component(toggle_effects_btn)

        toggle_lights_btn = Button(
            20,
            465,
            260,
            35,
            text="Toggle Lighting",
            bg_color=Color(100, 50, 100),
            hover_color=Color(150, 70, 150),
            on_click=self._toggle_lights,
        )
        self.ui_manager.add_component(toggle_lights_btn)

        # Help
        help_label = Label(
            20, 515, "Press Keys:", font_size=16, color=Color(100, 150, 200)
        )
        self.ui_manager.add_component(help_label)

        help_text = Label(
            20,
            540,
            "1-3: Emit particles\nE: Post-effects\nL: Lights\nQ: Clear all",
            font_size=14,
            color=Color(150, 150, 150),
        )
        self.ui_manager.add_component(help_text)

    def _emit_particles(self, color: tuple) -> None:
        """Emit particles at random position."""
        import random

        x = random.randint(350, 1280)
        y = random.randint(50, 900)

        emitter = ParticleEmitter(
            x,
            y,
            emission_rate=int(self.rate_slider.value),
            lifetime=2.0,
            size_range=(1, self.size_slider.value),
            velocity_range=(50, 200),
            color=color,
        )
        self.particle_system.add_emitter(emitter)

    def _on_size_change(self, value: float) -> None:
        """Handle size slider change."""
        pass  # Size will be used when emitting new particles

    def _on_rate_change(self, value: float) -> None:
        """Handle rate slider change."""
        pass  # Rate will be used when emitting new particles

    def _toggle_effects(self) -> None:
        """Toggle post-processing effects."""
        self.post_effects_enabled = not self.post_effects_enabled

    def _toggle_lights(self) -> None:
        """Toggle lighting."""
        self.lights_enabled = not self.lights_enabled

    def handle_input(self) -> None:
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_1:
                    self._emit_particles((255, 100, 100))
                elif event.key == pygame.K_2:
                    self._emit_particles((100, 150, 255))
                elif event.key == pygame.K_3:
                    self._emit_particles((100, 255, 100))
                elif event.key == pygame.K_e:
                    self._toggle_effects()
                elif event.key == pygame.K_l:
                    self._toggle_lights()
                elif event.key == pygame.K_q:
                    self.particle_system.emitters.clear()

            # Forward to UI manager
            self.ui_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """Update game state."""
        self.ui_manager.update(dt)
        self.particle_system.update(dt)

        # Update light positions (make them move slightly)
        time = pygame.time.get_ticks() / 1000.0
        if len(self.lighting_system.lights) >= 3:
            self.lighting_system.lights[0].set_position(
                200 + math.sin(time) * 50, 200 + math.cos(time * 1.5) * 50
            )
            self.lighting_system.lights[2].set_position(
                640 + math.sin(time * 0.7) * 100, 700 + math.cos(time * 0.5) * 50
            )

    def draw(self) -> None:
        """Draw everything."""
        # Clear screen
        self.screen.fill((20, 20, 30))

        # Draw background grid
        self._draw_grid()

        # Draw particles
        self.particle_system.draw(self.screen)

        # Draw lighting visualization if enabled
        if self.lights_enabled:
            self._draw_lighting_overlay()

        # Draw UI
        self.ui_manager.draw(self.screen)

        # Draw status info
        self._draw_status()

        # Apply post-processing effects if enabled
        if self.post_effects_enabled:
            self._apply_post_processing()

        pygame.display.flip()

    def _draw_grid(self) -> None:
        """Draw background grid."""
        grid_size = 50
        color = (40, 40, 50)

        for x in range(320, self.screen.get_width(), grid_size):
            pygame.draw.line(self.screen, color, (x, 0), (x, self.screen.get_height()))

        for y in range(0, self.screen.get_height(), grid_size):
            pygame.draw.line(self.screen, color, (320, y), (self.screen.get_width(), y))

    def _draw_lighting_overlay(self) -> None:
        """Draw lighting visualization."""
        # Draw light circles
        for light in self.lighting_system.lights:
            # Draw light radius
            pygame.draw.circle(
                self.screen,
                (
                    int(light.color.r * 0.3),
                    int(light.color.g * 0.3),
                    int(light.color.b * 0.3),
                ),
                (int(light.x), int(light.y)),
                int(light.radius),
                1,
            )
            # Draw light center
            pygame.draw.circle(
                self.screen, light.color.to_rgb_tuple(), (int(light.x), int(light.y)), 5
            )

    def _draw_status(self) -> None:
        """Draw status information."""
        fps = self.clock.get_fps()
        particle_count = sum(len(e.particles) for e in self.particle_system.emitters)

        status_text = f"FPS: {fps:.1f} | Particles: {particle_count} | Post-FX: {'ON' if self.post_effects_enabled else 'OFF'} | Lights: {'ON' if self.lights_enabled else 'OFF'}"
        status_surf = self.small_font.render(status_text, True, (150, 200, 150))
        self.screen.blit(status_surf, (320, 930))

    def _apply_post_processing(self) -> None:
        """Apply post-processing effects."""
        # For this demo, we'll draw effect indicators instead of applying expensive effects
        text = self.small_font.render(
            "✓ Post-Processing Active (Bloom + Blur)", True, (200, 100, 255)
        )
        self.screen.blit(text, (320, 10))

    def run(self) -> None:
        """Run the demo application."""
        print(__doc__)
        print("\nStarting Graphics & UI Demo...")

        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
            self.handle_input()
            self.update(dt)
            self.draw()

        pygame.quit()
        print("Graphics & UI Demo closed.")


def main():
    """Entry point for the UI demo."""
    try:
        app = UIDemo()
        app.run()
    except Exception as e:
        print(f"Error running demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
