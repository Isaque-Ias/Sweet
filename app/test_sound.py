"""
Interactive Sound System Test & Demo

Demonstrates all sound system features:
- Sound playback with volume control
- Multiple simultaneous sounds
- Background music with crossfading
- 3D audio positioning
- Sound pooling
- Volume management

Controls:
  1-9: Play different sounds
  M: Play/stop background music
  F: Crossfade to different music
  Arrow Keys: Move listener position (for 3D audio)
  +/-: Increase/decrease master volume
  O/P: Increase/decrease music volume
  I/U: Increase/decrease SFX volume
  SPACE: Pause/unpause current music
  ESC: Exit demo
"""

import sys
import os
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from sweet.sound import (
    SoundManager,
    init_sound_manager,
    AudioFormat,
    Vec3D,
    Sound3DConfig,
)


class SoundDemoApp:
    """Interactive sound system demonstration."""

    def __init__(self):
        """Initialize the demo application."""
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 768))
        pygame.display.set_caption("Sweet Engine - Sound System Demo")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.running = True

        # Initialize sound manager
        self.sound_manager = init_sound_manager(frequency=22050, channels=2)

        # Create demo sounds
        self._create_demo_sounds()

        # 3D audio state
        self.listener_pos = Vec3D(512, 384, 0)
        self.sound_positions = {
            "ping_1": Vec3D(200, 200, 0),
            "ping_2": Vec3D(800, 200, 0),
            "ping_3": Vec3D(200, 600, 0),
            "ping_4": Vec3D(800, 600, 0),
        }

        # State tracking
        self.music_playing = False
        self.active_sounds = []
        self.show_help = True

    def _create_demo_sounds(self) -> None:
        """Create synthetic demo sounds using pygame."""
        # This creates simple beep sounds with different frequencies
        # In a real game, you'd load actual audio files

        sounds_data = {
            "ping_low": 220,  # A3
            "ping_mid": 440,  # A4
            "ping_high": 880,  # A5
            "beep_short": 1000,  # High beep
            "sweep_up": None,  # Frequency sweep
            "sweep_down": None,  # Frequency sweep
            "blip": 600,  # Short blip
            "chirp": 800,  # Chirp sound
            "music_loop": None,  # Background music
        }

        # Generate synthetic sounds
        for name, freq in sounds_data.items():
            if freq is not None:
                # Generate a sine wave sound
                sample_rate = 22050
                duration = 0.5  # 500ms
                frames = int(sample_rate * duration)

                sound_array = []
                for i in range(frames):
                    t = i / sample_rate
                    # Simple sine wave
                    sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * t))
                    sound_array.append(sample)
                    sound_array.append(sample)  # Stereo

                sound = pygame.mixer.Sound(buffer=bytes(sound_array))
                # Save to temporary file
                self._save_wav(f"/tmp/{name}.wav", sound, sample_rate)

                try:
                    self.sound_manager.load_sound(
                        name,
                        f"/tmp/{name}.wav",
                        AudioFormat.WAV,
                        is_music=False,
                        volume=0.7,
                    )
                except Exception as e:
                    print(f"Note: Could not load {name}: {e}")
            else:
                # Generate music/sweep sounds
                if name == "sweep_up":
                    self._generate_sweep_sound(name, 400, 800, 1.0)
                elif name == "sweep_down":
                    self._generate_sweep_sound(name, 800, 400, 1.0)
                elif name == "music_loop":
                    self._generate_music_sound(name)

    def _generate_sweep_sound(
        self, name: str, start_freq: int, end_freq: int, duration: float
    ) -> None:
        """Generate a frequency sweep sound."""
        sample_rate = 22050
        frames = int(sample_rate * duration)
        sound_array = []

        for i in range(frames):
            t = i / sample_rate
            progress = t / duration
            freq = start_freq + (end_freq - start_freq) * progress

            sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * t))
            sound_array.append(sample)
            sound_array.append(sample)

        sound = pygame.mixer.Sound(buffer=bytes(sound_array))
        self._save_wav(f"/tmp/{name}.wav", sound, sample_rate)

        try:
            self.sound_manager.load_sound(
                name, f"/tmp/{name}.wav", AudioFormat.WAV, is_music=False, volume=0.7
            )
        except Exception as e:
            print(f"Note: Could not load {name}: {e}")

    def _generate_music_sound(self, name: str) -> None:
        """Generate a simple loopable music sound."""
        sample_rate = 22050
        duration = 4.0  # 4 second loop
        frames = int(sample_rate * duration)
        sound_array = []

        for i in range(frames):
            t = i / sample_rate
            beat = t % 1.0  # 1 second per beat

            if beat < 0.25:
                freq = 440
            elif beat < 0.5:
                freq = 330
            elif beat < 0.75:
                freq = 392
            else:
                freq = 440

            sample = int(32767 * 0.2 * math.sin(2 * math.pi * freq * t))
            sound_array.append(sample)
            sound_array.append(sample)

        sound = pygame.mixer.Sound(buffer=bytes(sound_array))
        self._save_wav(f"/tmp/{name}.wav", sound, sample_rate)

        try:
            self.sound_manager.load_sound(
                name, f"/tmp/{name}.wav", AudioFormat.WAV, is_music=True, volume=0.5
            )
        except Exception as e:
            print(f"Note: Could not load {name}: {e}")

    def _save_wav(
        self, filepath: str, sound: pygame.mixer.Sound, sample_rate: int
    ) -> None:
        """Save pygame Sound to WAV file (simplified)."""
        import struct
        import io

        # Get sound array
        sound_array = pygame.sndarray.array(sound)

        # Create WAV file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, "wb") as f:
                # WAV header
                f.write(b"RIFF")
                f.write(struct.pack("<I", 36 + len(sound_array) * 2))
                f.write(b"WAVE")
                f.write(b"fmt ")
                f.write(struct.pack("<I", 16))  # Subchunk1Size
                f.write(struct.pack("<H", 1))  # AudioFormat (PCM)
                f.write(struct.pack("<H", 2))  # NumChannels (stereo)
                f.write(struct.pack("<I", sample_rate))  # SampleRate
                f.write(struct.pack("<I", sample_rate * 2 * 2))  # ByteRate
                f.write(struct.pack("<H", 4))  # BlockAlign
                f.write(struct.pack("<H", 16))  # BitsPerSample
                f.write(b"data")
                f.write(struct.pack("<I", len(sound_array) * 2))

                # Sound data
                for sample in sound_array:
                    f.write(struct.pack("<h", min(32767, max(-32768, sample))))
        except Exception as e:
            print(f"Warning: Could not save WAV file: {e}")

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
                elif event.key in range(pygame.K_1, pygame.K_9 + 1):
                    # Play sounds 1-9
                    sound_num = event.key - pygame.K_1 + 1
                    self._play_sound_by_number(sound_num)
                elif event.key == pygame.K_m:
                    # Toggle music
                    if self.music_playing:
                        self.sound_manager.stop_music(fade_ms=500)
                        self.music_playing = False
                    else:
                        try:
                            self.sound_manager.play_music("music_loop", loops=-1)
                            self.music_playing = True
                        except KeyError:
                            pass
                elif event.key == pygame.K_f:
                    # Crossfade music
                    try:
                        self.sound_manager.play_music(
                            "music_loop", loops=-1, crossfade_duration=2000
                        )
                        self.music_playing = True
                    except KeyError:
                        pass
                elif event.key == pygame.K_SPACE:
                    # Pause/unpause music
                    if self.music_playing:
                        try:
                            import pygame.mixer

                            if pygame.mixer.music.get_busy():
                                pygame.mixer.music.pause()
                            else:
                                pygame.mixer.music.unpause()
                        except:
                            pass
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    # Increase master volume
                    vol = self.sound_manager.master_volume + 0.1
                    self.sound_manager.set_master_volume(vol)
                elif event.key == pygame.K_MINUS:
                    # Decrease master volume
                    vol = self.sound_manager.master_volume - 0.1
                    self.sound_manager.set_master_volume(vol)
                elif event.key == pygame.K_o:
                    # Decrease music volume
                    vol = self.sound_manager.music_volume - 0.1
                    self.sound_manager.set_music_volume(vol)
                elif event.key == pygame.K_p:
                    # Increase music volume
                    vol = self.sound_manager.music_volume + 0.1
                    self.sound_manager.set_music_volume(vol)
                elif event.key == pygame.K_i:
                    # Decrease SFX volume
                    vol = self.sound_manager.sfx_volume - 0.1
                    self.sound_manager.set_sfx_volume(vol)
                elif event.key == pygame.K_u:
                    # Increase SFX volume
                    vol = self.sound_manager.sfx_volume + 0.1
                    self.sound_manager.set_sfx_volume(vol)

        # Arrow keys for listener movement (3D audio)
        keys = pygame.key.get_pressed()
        speed = 5
        if keys[pygame.K_LEFT]:
            self.listener_pos.x -= speed
        if keys[pygame.K_RIGHT]:
            self.listener_pos.x += speed
        if keys[pygame.K_UP]:
            self.listener_pos.y -= speed
        if keys[pygame.K_DOWN]:
            self.listener_pos.y += speed

    def _play_sound_by_number(self, num: int) -> None:
        """Play a sound by number."""
        sound_names = [
            "ping_low",
            "ping_mid",
            "ping_high",
            "beep_short",
            "sweep_up",
            "sweep_down",
            "blip",
            "chirp",
            "music_loop",
        ]

        if num <= len(sound_names):
            try:
                name = sound_names[num - 1]
                self.sound_manager.play(name, volume=0.7)
                if name not in self.active_sounds:
                    self.active_sounds.append(name)
            except KeyError:
                pass

    def update(self) -> None:
        """Update game state."""
        # Update listener position for 3D audio
        self.sound_manager.set_listener_position(self.listener_pos)
        self.sound_manager.update_3d_audio()

    def draw(self) -> None:
        """Draw the demo interface."""
        self.screen.fill((20, 20, 30))

        y_offset = 20

        # Title
        title = self.font.render(
            "🎵 Sweet Engine - Sound System Demo", True, (100, 200, 255)
        )
        self.screen.blit(title, (20, y_offset))
        y_offset += 40

        # Status
        status_text = f"Master Vol: {self.sound_manager.master_volume:.1f} | Music Vol: {self.sound_manager.music_volume:.1f} | SFX Vol: {self.sound_manager.sfx_volume:.1f}"
        status = self.small_font.render(status_text, True, (150, 150, 150))
        self.screen.blit(status, (20, y_offset))
        y_offset += 30

        active_count = self.sound_manager.get_active_sound_count()
        music_status = "Playing" if self.music_playing else "Stopped"
        info = self.small_font.render(
            f"Active Sounds: {active_count} | Music: {music_status} | Listener: ({self.listener_pos.x:.0f}, {self.listener_pos.y:.0f})",
            True,
            (150, 200, 150),
        )
        self.screen.blit(info, (20, y_offset))
        y_offset += 30

        # Help text
        if self.show_help:
            y_offset += 10
            help_items = [
                "KEYS:",
                "1-9: Play sounds (1=ping_low, 2=ping_mid, 3=ping_high, 4=beep, 5=sweep_up, 6=sweep_down, 7=blip, 8=chirp, 9=music)",
                "M: Play/Stop Music | F: Crossfade Music | SPACE: Pause/Unpause",
                "Arrows: Move Listener (for 3D audio positioning)",
                "+/-: Master Volume | O/P: Music Volume | I/U: SFX Volume",
                "H: Toggle Help | ESC: Exit",
            ]

            for item in help_items:
                text = self.small_font.render(item, True, (200, 200, 100))
                self.screen.blit(text, (20, y_offset))
                y_offset += 25
        else:
            help_hint = self.small_font.render(
                "Press H for help", True, (100, 100, 100)
            )
            self.screen.blit(help_hint, (20, y_offset))

        # Visual representation of 3D audio positions
        y_offset += 40
        title_3d = self.font.render(
            "3D Audio Visualization (Top-down view):", True, (100, 200, 255)
        )
        self.screen.blit(title_3d, (20, y_offset))
        y_offset += 35

        # Draw minimap
        minimap_size = 300
        minimap_x = 20
        minimap_y = y_offset

        pygame.draw.rect(
            self.screen,
            (50, 50, 60),
            (minimap_x, minimap_y, minimap_size, minimap_size),
        )
        pygame.draw.rect(
            self.screen,
            (100, 100, 120),
            (minimap_x, minimap_y, minimap_size, minimap_size),
            2,
        )

        # Draw sound sources
        for name, pos in self.sound_positions.items():
            scale_x = minimap_size / 1024
            scale_y = minimap_size / 768
            x = minimap_x + pos.x * scale_x
            y = minimap_y + pos.y * scale_y
            pygame.draw.circle(self.screen, (255, 100, 100), (int(x), int(y)), 5)

        # Draw listener
        listen_scale_x = minimap_size / 1024
        listen_scale_y = minimap_size / 768
        listen_x = minimap_x + self.listener_pos.x * listen_scale_x
        listen_y = minimap_y + self.listener_pos.y * listen_scale_y
        pygame.draw.circle(
            self.screen, (100, 255, 100), (int(listen_x), int(listen_y)), 8
        )

        # Add labels
        label = self.small_font.render(
            "Green = Listener, Red = Sound Sources", True, (150, 150, 150)
        )
        self.screen.blit(label, (minimap_x, minimap_y + minimap_size + 10))

        pygame.display.flip()

    def run(self) -> None:
        """Run the demo application."""
        print(__doc__)
        print("\nStarting Sound System Demo...")

        while self.running:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(60)

        self.sound_manager.shutdown()
        pygame.quit()
        print("Sound Demo closed.")


def main():
    """Entry point for the sound demo."""
    try:
        app = SoundDemoApp()
        app.run()
    except Exception as e:
        print(f"Error running demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
