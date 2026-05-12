"""
Sound System Module

Provides a comprehensive audio management system with support for:
- Multiple audio formats (WAV, OGG, MP3)
- Sound manager with volume and playback controls
- 3D audio positioning and attenuation
- Background music system with crossfading
- Sound pooling for efficient resource usage
"""

import pygame
import os
import math
from typing import Dict, Optional, Tuple, List, Callable
from enum import Enum
from dataclasses import dataclass
import threading
import time


class AudioFormat(Enum):
    """Supported audio formats."""

    WAV = "wav"
    OGG = "ogg"
    MP3 = "mp3"


@dataclass
class Vec3D:
    """Simple 3D vector for audio positioning."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: "Vec3D") -> float:
        """Calculate distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def angle_to(self, other: "Vec3D") -> float:
        """Calculate angle to another point (in radians, in XY plane)."""
        dx = other.x - self.x
        dy = other.y - self.y
        return math.atan2(dy, dx)


@dataclass
class Sound3DConfig:
    """Configuration for 3D audio positioning."""

    max_distance: float = 1000.0  # Distance at which sound becomes silent
    reference_distance: float = 100.0  # Distance at which sound is at full volume
    attenuation_factor: float = 1.0  # How quickly sound attenuates with distance
    use_panning: bool = True  # Apply stereo panning based on position
    use_distance_volume: bool = True  # Apply volume attenuation based on distance


class SoundSource:
    """Represents a single sound that can be played."""

    def __init__(
        self,
        file_path: str,
        format_type: AudioFormat,
        is_music: bool = False,
        volume: float = 1.0,
    ):
        """
        Initialize a sound source.

        Args:
            file_path: Path to the audio file
            format_type: Audio format (WAV, OGG, MP3)
            is_music: Whether this is background music
            volume: Initial volume (0.0 to 1.0)

        Raises:
            FileNotFoundError: If audio file doesn't exist
            pygame.error: If audio format is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        self.file_path = file_path
        self.format = format_type
        self.is_music = is_music
        self.volume = max(0.0, min(1.0, volume))
        self.sound = None
        self.channel = None
        self.is_playing = False
        self.loops = 0
        self.position_3d = Vec3D()
        self.listener_position = Vec3D()
        self.pan = 0.0  # -1.0 (left) to 1.0 (right)

        self._load_sound()

    def _load_sound(self) -> None:
        """Load the sound file."""
        try:
            if self.format == AudioFormat.MP3:
                # pygame.mixer has limited MP3 support on some systems
                # This will work if pygame was compiled with MP3 support
                self.sound = pygame.mixer.Sound(self.file_path)
            elif self.format == AudioFormat.OGG:
                self.sound = pygame.mixer.Sound(self.file_path)
            elif self.format == AudioFormat.WAV:
                self.sound = pygame.mixer.Sound(self.file_path)
            else:
                raise ValueError(f"Unsupported format: {self.format}")
        except pygame.error as e:
            raise pygame.error(f"Failed to load audio file {self.file_path}: {e}")

        self.sound.set_volume(self.volume)

    def play(self, loops: int = 0, fade_ms: int = 0) -> Optional[int]:
        """
        Play the sound.

        Args:
            loops: Number of loops (-1 for infinite)
            fade_ms: Fade in duration in milliseconds

        Returns:
            Channel ID if successful, None otherwise
        """
        if self.is_music:
            try:
                pygame.mixer.music.load(self.file_path)
                pygame.mixer.music.set_volume(self.volume)
                if fade_ms > 0:
                    pygame.mixer.music.play(loops, fade_ms=fade_ms)
                else:
                    pygame.mixer.music.play(loops)
                self.is_playing = True
                self.loops = loops
                return 0  # Music uses channel 0
            except pygame.error as e:
                raise pygame.error(f"Failed to play music: {e}")
        else:
            try:
                self.channel = self.sound.play(loops, fade_ms=fade_ms)
                self.is_playing = self.channel is not None
                self.loops = loops
                return self.channel.get_channel() if self.channel else None
            except pygame.error as e:
                raise pygame.error(f"Failed to play sound: {e}")

    def stop(self, fade_ms: int = 0) -> None:
        """
        Stop the sound.

        Args:
            fade_ms: Fade out duration in milliseconds
        """
        if self.is_music:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
        else:
            if self.channel and fade_ms > 0:
                self.channel.fadeout(fade_ms)
            elif self.channel:
                self.channel.stop()

        self.is_playing = False

    def pause(self) -> None:
        """Pause the sound."""
        if self.is_music:
            pygame.mixer.music.pause()
        elif self.channel:
            self.channel.pause()

    def unpause(self) -> None:
        """Unpause the sound."""
        if self.is_music:
            pygame.mixer.music.unpause()
        elif self.channel:
            self.channel.unpause()

    def set_volume(self, volume: float) -> None:
        """Set sound volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        if self.is_music:
            pygame.mixer.music.set_volume(self.volume)
        elif self.sound:
            self.sound.set_volume(self.volume)

    def get_busy(self) -> bool:
        """Check if sound is currently playing."""
        if self.is_music:
            return pygame.mixer.music.get_busy()
        elif self.channel:
            return self.channel.get_busy()
        return False

    def update_3d_position(
        self,
        source_pos: Vec3D,
        listener_pos: Vec3D,
        config: Sound3DConfig,
    ) -> None:
        """
        Update 3D audio properties (panning and volume attenuation).

        Args:
            source_pos: Position of the sound source
            listener_pos: Position of the listener
            config: 3D audio configuration
        """
        self.position_3d = source_pos
        self.listener_position = listener_pos

        # Calculate distance-based attenuation
        distance = source_pos.distance_to(listener_pos)

        if config.use_distance_volume:
            if distance <= config.reference_distance:
                volume_factor = 1.0
            elif distance >= config.max_distance:
                volume_factor = 0.0
            else:
                # Logarithmic attenuation
                ratio = distance / config.reference_distance
                volume_factor = 1.0 / (ratio**config.attenuation_factor)
        else:
            volume_factor = 1.0

        # Apply panning based on angle
        if config.use_panning and not self.is_music:
            angle = listener_pos.angle_to(source_pos)
            # Normalize angle to -180 to 180
            while angle > math.pi:
                angle -= 2 * math.pi
            while angle < -math.pi:
                angle += 2 * math.pi
            # Convert to pan value -1.0 to 1.0
            self.pan = angle / math.pi
            # Note: pygame.mixer doesn't have built-in panning for individual channels
            # This is stored for reference; actual panning would require manual stereo mixing

        # Update effective volume
        if not self.is_music and self.channel:
            effective_volume = self.volume * volume_factor
            self.channel.set_volume(effective_volume)


class SoundPool:
    """Pool of reusable sound sources for efficient memory usage."""

    def __init__(self, format_type: AudioFormat, pool_size: int = 10):
        """
        Initialize a sound pool.

        Args:
            format_type: Audio format for pooled sounds
            pool_size: Maximum number of simultaneous sounds
        """
        self.format_type = format_type
        self.pool_size = pool_size
        self.available: List[SoundSource] = []
        self.in_use: List[SoundSource] = []

    def acquire(self, file_path: str, volume: float = 1.0) -> SoundSource:
        """
        Get a sound source from the pool.

        Args:
            file_path: Path to audio file
            volume: Initial volume

        Returns:
            A SoundSource instance
        """
        # Try to reuse a stopped sound from the pool
        for sound in self.available[:]:
            if not sound.get_busy():
                self.available.remove(sound)
                sound.file_path = file_path
                sound._load_sound()
                sound.set_volume(volume)
                self.in_use.append(sound)
                return sound

        # If pool not full, create new sound
        if len(self.available) + len(self.in_use) < self.pool_size:
            sound = SoundSource(file_path, self.format_type, volume=volume)
            self.in_use.append(sound)
            return sound

        # Pool is full; use least-recently-used
        if self.available:
            sound = self.available.pop(0)
        elif self.in_use:
            sound = self.in_use.pop(0)
        else:
            sound = SoundSource(file_path, self.format_type, volume=volume)

        sound.stop()
        sound.file_path = file_path
        sound._load_sound()
        sound.set_volume(volume)
        self.in_use.append(sound)
        return sound

    def release(self, sound: SoundSource) -> None:
        """Release a sound back to the pool."""
        if sound in self.in_use:
            self.in_use.remove(sound)
            self.available.append(sound)

    def cleanup(self) -> None:
        """Clean up all pooled sounds."""
        self.available.clear()
        self.in_use.clear()


class SoundManager:
    """
    Central manager for all audio playback and 3D positioning.

    Provides:
    - Sound playback with volume control
    - Background music management with crossfading
    - 3D audio positioning
    - Sound pooling
    - Global volume control
    """

    def __init__(self, frequency: int = 22050, channels: int = 2):
        """
        Initialize the SoundManager.

        Args:
            frequency: Sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
        """
        self.frequency = frequency
        self.channels = channels
        self.master_volume = 1.0
        self.music_volume = 1.0
        self.sfx_volume = 1.0

        self.listener_position = Vec3D()
        self.sound_3d_config = Sound3DConfig()

        self.sounds: Dict[str, SoundSource] = {}
        self.active_sounds: List[SoundSource] = []
        self.current_music: Optional[SoundSource] = None
        self.music_crossfade_thread: Optional[threading.Thread] = None
        self.music_fade_duration = 0

        self.pools: Dict[AudioFormat, SoundPool] = {
            fmt: SoundPool(fmt, pool_size=16) for fmt in AudioFormat
        }

        self._initialize_mixer()

    def _initialize_mixer(self) -> None:
        """Initialize pygame.mixer with appropriate settings."""
        try:
            pygame.mixer.init(
                frequency=self.frequency,
                channels=self.channels,
                buffer=512,
            )
        except pygame.error as e:
            raise RuntimeError(f"Failed to initialize audio mixer: {e}")

    def load_sound(
        self,
        name: str,
        file_path: str,
        format_type: AudioFormat,
        is_music: bool = False,
        volume: float = 1.0,
    ) -> SoundSource:
        """
        Load a sound into memory.

        Args:
            name: Unique identifier for the sound
            file_path: Path to the audio file
            format_type: Audio format
            is_music: Whether this is background music
            volume: Initial volume (0.0 to 1.0)

        Returns:
            The loaded SoundSource

        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If sound with name already loaded
        """
        if name in self.sounds:
            raise ValueError(f"Sound '{name}' already loaded")

        try:
            sound = SoundSource(file_path, format_type, is_music, volume)
            self.sounds[name] = sound
            return sound
        except (FileNotFoundError, pygame.error) as e:
            raise RuntimeError(f"Failed to load sound '{name}': {e}")

    def play(
        self,
        name: str,
        loops: int = 0,
        fade_ms: int = 0,
        volume: Optional[float] = None,
    ) -> Optional[int]:
        """
        Play a loaded sound.

        Args:
            name: Name of the loaded sound
            loops: Number of loops (-1 for infinite)
            fade_ms: Fade in duration in milliseconds
            volume: Override volume (0.0 to 1.0)

        Returns:
            Channel ID if successful, None otherwise

        Raises:
            KeyError: If sound not loaded
        """
        if name not in self.sounds:
            raise KeyError(f"Sound '{name}' not loaded")

        sound = self.sounds[name]

        if volume is not None:
            sound.set_volume(volume * self.sfx_volume * self.master_volume)

        channel = sound.play(loops, fade_ms)
        if channel is not None:
            self.active_sounds.append(sound)

        return channel

    def stop(self, name: str, fade_ms: int = 0) -> None:
        """
        Stop a playing sound.

        Args:
            name: Name of the sound
            fade_ms: Fade out duration in milliseconds

        Raises:
            KeyError: If sound not loaded
        """
        if name not in self.sounds:
            raise KeyError(f"Sound '{name}' not loaded")

        self.sounds[name].stop(fade_ms)
        if self.sounds[name] in self.active_sounds:
            self.active_sounds.remove(self.sounds[name])

    def pause(self, name: str) -> None:
        """Pause a sound."""
        if name in self.sounds:
            self.sounds[name].pause()

    def unpause(self, name: str) -> None:
        """Unpause a sound."""
        if name in self.sounds:
            self.sounds[name].unpause()

    def play_music(
        self,
        name: str,
        loops: int = -1,
        fade_ms: int = 0,
        crossfade_duration: int = 0,
    ) -> None:
        """
        Play background music, optionally crossfading from current music.

        Args:
            name: Name of the music track
            loops: Number of loops (-1 for infinite)
            fade_ms: Fade in duration
            crossfade_duration: Duration of crossfade from previous music (ms)

        Raises:
            KeyError: If music not loaded
        """
        if name not in self.sounds:
            raise KeyError(f"Music '{name}' not loaded")

        new_music = self.sounds[name]

        if crossfade_duration > 0 and self.current_music:
            # Stop crossfade thread if running
            if self.music_crossfade_thread and self.music_crossfade_thread.is_alive():
                pass  # Wait for it to finish

            # Start crossfade
            self.music_crossfade_thread = threading.Thread(
                target=self._crossfade_music,
                args=(
                    self.current_music,
                    new_music,
                    crossfade_duration,
                    loops,
                    fade_ms,
                ),
                daemon=True,
            )
            self.music_crossfade_thread.start()
        else:
            if self.current_music:
                self.current_music.stop(fade_ms if fade_ms > 0 else 0)

            new_music.play(loops, fade_ms)
            self.current_music = new_music

    def _crossfade_music(
        self,
        old_music: SoundSource,
        new_music: SoundSource,
        duration: int,
        loops: int,
        fade_ms: int,
    ) -> None:
        """Crossfade between two music tracks."""
        steps = 20
        step_duration = duration / steps
        old_volume = old_music.volume
        new_volume = new_music.volume

        # Start playing new music silently
        new_music.sound.set_volume(0.0)
        new_music.play(loops, fade_ms=0)

        # Crossfade
        for i in range(steps + 1):
            progress = i / steps
            old_music.set_volume(old_volume * (1 - progress))
            new_music.set_volume(new_volume * progress)
            time.sleep(step_duration / 1000.0)

        # Stop old music
        old_music.stop()
        self.current_music = new_music

    def stop_music(self, fade_ms: int = 0) -> None:
        """Stop current background music."""
        if self.current_music:
            self.current_music.stop(fade_ms)
            self.current_music = None

    def set_listener_position(self, position: Vec3D) -> None:
        """Set the listener (player) position for 3D audio."""
        self.listener_position = position

    def update_3d_audio(self) -> None:
        """Update 3D audio positioning for all active sounds."""
        for sound in self.active_sounds[:]:
            if sound.get_busy():
                sound.update_3d_position(
                    sound.position_3d,
                    self.listener_position,
                    self.sound_3d_config,
                )
            else:
                self.active_sounds.remove(sound)

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def set_music_volume(self, volume: float) -> None:
        """Set music volume (0.0 to 1.0)."""
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def set_sfx_volume(self, volume: float) -> None:
        """Set SFX volume (0.0 to 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            if not sound.is_music:
                sound.set_volume(sound.volume * self.sfx_volume * self.master_volume)

    def set_3d_config(self, config: Sound3DConfig) -> None:
        """Update 3D audio configuration."""
        self.sound_3d_config = config

    def get_active_sound_count(self) -> int:
        """Get number of currently playing sounds."""
        return len([s for s in self.active_sounds if s.get_busy()])

    def get_sound_names(self) -> List[str]:
        """Get list of all loaded sound names."""
        return list(self.sounds.keys())

    def unload_sound(self, name: str) -> None:
        """Unload a sound from memory."""
        if name in self.sounds:
            sound = self.sounds[name]
            sound.stop()
            del self.sounds[name]
            if sound in self.active_sounds:
                self.active_sounds.remove(sound)

    def shutdown(self) -> None:
        """Shut down the sound system."""
        self.stop_music()
        for sound in self.sounds.values():
            sound.stop()
        self.sounds.clear()
        self.active_sounds.clear()

        for pool in self.pools.values():
            pool.cleanup()

        try:
            pygame.mixer.quit()
        except pygame.error:
            pass


# Global sound manager instance
_global_sound_manager: Optional[SoundManager] = None


def init_sound_manager(frequency: int = 22050, channels: int = 2) -> SoundManager:
    """
    Initialize the global sound manager.

    Args:
        frequency: Sample rate in Hz
        channels: Number of audio channels

    Returns:
        The initialized SoundManager
    """
    global _global_sound_manager
    _global_sound_manager = SoundManager(frequency, channels)
    return _global_sound_manager


def get_sound_manager() -> SoundManager:
    """
    Get the global sound manager.

    Returns:
        The SoundManager instance

    Raises:
        RuntimeError: If sound manager not initialized
    """
    if _global_sound_manager is None:
        raise RuntimeError(
            "Sound manager not initialized. Call init_sound_manager() first."
        )
    return _global_sound_manager
