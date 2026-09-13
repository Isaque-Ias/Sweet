from __future__ import annotations
import struct
import moderngl
from typing import Any, Optional, TYPE_CHECKING
from ..graphics.render.process import PipelineManager
from .view import View
from abc import ABC, abstractmethod
import numpy as np
from ..plataform.hal.manager import GraphicsDevice
import math
if TYPE_CHECKING:
    from .scene import Scene

graphics_device: GraphicsDevice

class SkyBox(ABC):
    @abstractmethod
    def update(self, **kwargs: Any):
        pass

    @property
    def scene(self) -> Any:
        pass

    @scene.setter
    def scene(self, value: Scene) -> None:
        pass

    @property
    def target(self) -> Any:
        pass

    @target.setter
    def target(self, value: Any) -> None:
        pass

    @property
    def resolution(self) -> Any:
        pass

    @resolution.setter
    def resolution(self, value: int) -> None:
        pass

class NishitaSkyBox(SkyBox):
    def __init__(self):
        self.type = type
        self.views: list[View] = []
        self._scene: Optional[Scene] = None

        self._resolution = 512
        self._cubemap = graphics_device.create_cubemap_framebuffer(self._resolution, [4], 4, dtype="f2")
        self._cubemap.set_filters(moderngl.LINEAR, moderngl.LINEAR)
        self._target = self._cubemap.get_target()

    def _get_sun_parameters(self, time_ticks: int, horizontal_deg: float, weather: str = "clear"):
        # 1. Map 24,000 ticks directly to altitude angle in RADIANS [-pi/2 to +pi/2]
        # Ticks: 0 -> -pi/2 (-90° midnight), 6000 -> 0 (0° sunrise), 12000 -> +pi/2 (+90° noon), 18000 -> 0 (sunset)
        time_normalized = (time_ticks % 24000) / 24000.0
        altitude_rad = (time_normalized - 0.25) * 2.0 * math.pi
        
        # 2. Compute Direction Vector
        azimuth_rad = math.radians(horizontal_deg)
        cos_alt = math.cos(altitude_rad)
        
        x = cos_alt * math.sin(azimuth_rad)
        y = math.sin(altitude_rad)  # Height / Sine of altitude
        z = cos_alt * math.cos(azimuth_rad)
        
        # Normalize direction vector
        length = math.sqrt(x*x + y*y + z*z)
        sun_direction = (x / length, y / length, z / length)
        
        # 3. Calculate Illuminance (Lux) with Twilight Smoothness
        if y <= -0.2: 
            # Deep Night (Sun >11.5° below horizon): Pure Moonlight (~0.25 lux)
            base_lux = 0.25
        elif y <= 0.0:
            # Twilight Zone (-11.5° to 0° altitude): Exponential sky glow scatter (0.25 to ~400 lux)
            # Smooth step mapping y from [-0.2, 0.0] to [0.0, 1.0]
            t = (y + 0.2) / 0.2
            base_lux = 0.25 + (399.75 * (t ** 3))
        else:
            # Sun Above Horizon: Direct Sunlight scaling with elevation angle + atmospheric base (~400 to 120,000 lux)
            direct_sun_lux = 400.0 + (119600.0 * math.sin(altitude_rad))
            
            weather_multipliers = {
                "clear": 1.0,
                "sunset": 0.50,
                "overcast": 0.20,
                "storm": 0.03
            }
            
            base_lux = direct_sun_lux * weather_multipliers.get(weather.lower(), 1.0)
        
        sun_intensity = round(base_lux, 2)
        sun_direction = (round(sun_direction[0], 3), round(sun_direction[1], 3), round(sun_direction[2], 3))
        
        return sun_direction, sun_intensity

    EARTH_RADIUS = 6371000.0
    ATM_RADIUS   = 6471000.0
    HR           = 8000.0
    HM           = 1200.0

    BETA_R = np.array([5.8e-6, 1.35e-5, 3.31e-5], dtype=np.float32)
    BETA_M = np.array([4.0e-6, 4.0e-6, 4.0e-6], dtype=np.float32)

    @staticmethod
    def _cpu_ray_sphere_intersect(ro, rd, radius):
        b = np.dot(ro, rd)
        c = np.dot(ro, ro) - radius * radius
        d = b * b - c
        if d < 0.0:
            return np.array([-1.0, -1.0], dtype=np.float32)
        sqrt_d = np.sqrt(d)
        return np.array([-b - sqrt_d, -b + sqrt_d], dtype=np.float32)

    def _calculate_sun_and_ambient(self, camera_pos, sun_direction, base_sun_intensity):
        ray_origin = camera_pos + np.array([0.0, self.EARTH_RADIUS, 0.0], dtype=np.float32)

        sun_elevation = sun_direction[1]
        if sun_elevation < -0.1:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32), np.array([0.02, 0.02, 0.02], dtype=np.float32)

        hit_sun_atm = self._cpu_ray_sphere_intersect(ray_origin, sun_direction, self.ATM_RADIUS)
        light_step_size = hit_sun_atm[1] / 8.0
        
        optical_depth_r = 0.0
        optical_depth_m = 0.0

        for j in range(8):
            light_sample_pos = ray_origin + sun_direction * ((float(j) + 0.5) * light_step_size)
            light_height = np.linalg.norm(light_sample_pos) - self.EARTH_RADIUS
            if light_height < 0.0:
                light_height = 0.0

            optical_depth_r += np.exp(-light_height / self.HR) * light_step_size
            optical_depth_m += np.exp(-light_height / self.HM) * light_step_size

        # Beer's Law for sun attenuation through the atmosphere
        tau = self.BETA_R * optical_depth_r + self.BETA_M * 1.1 * optical_depth_m
        sun_attenuation = np.exp(-tau)
        
        sun_color = base_sun_intensity * sun_attenuation

        # 2. Calculate Ambient Color (Approximated via Zenith / Overhead Sky Direction)
        zenith_dir = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        cos_theta = np.dot(zenith_dir, sun_direction)
        phase_r = (3.0 / (16.0 * np.pi)) * (1.0 + cos_theta * cos_theta)
        
        # Approximate overhead sky scattering luminance
        zenith_sky = base_sun_intensity * (self.BETA_R * phase_r * 0.0005)
        
        # Combine zenith sky with a minimum ambient floor
        ambient_color = np.maximum(zenith_sky, np.array([0.03, 0.03, 0.03], dtype=np.float32)) + (sun_color * 0.05)

        return sun_color, ambient_color

    def apply_hdr_pipeline(self, hdr_rgb, ev100=15.0):
        """
        Applies camera exposure and ACES Filmic Tonemapping to convert 
        raw physical HDR light values to standard LDR display colors [0.0, 1.0].
        
        :param hdr_rgb: Tuple/List/Array of RGB light values (e.g., [80034.27, 73964.86, 60512.10])
        :param ev100: Exposure Value at ISO 100. 
                    Bright daylight = 14.0 to 15.0
                    Overcast / Sunset = 10.0 to 12.0
                    Night / Moonlight = -2.0 to 2.0
        """
        hdr = np.array(hdr_rgb, dtype=np.float32)
        
        # 1. Convert EV100 to Photometric Exposure Scale Factor
        # Photometric relationship: Exposure = 1 / (1.2 * 2^EV100)
        exposure_scale = 1.0 / (1.2 * (2.0 ** ev100))
        exposed_rgb = hdr * exposure_scale

        # 2. ACES Filmic Tonemapping Curve (Narkowicz fit)
        # Curves highlights gracefully to avoid hard white clipping
        a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
        tonemapped_rgb = (exposed_rgb * (a * exposed_rgb + b)) / (exposed_rgb * (c * exposed_rgb + d) + e)
        
        # 3. Clamp final values to valid [0.0, 1.0] display bounds
        ldr_rgb = np.clip(tonemapped_rgb, 0.0, 1.0)
        
        return ldr_rgb

    def update(self, **kwargs: Any):
        time: int = kwargs.get("time", 6000)
        direction: float = kwargs.get("direction", 0)
        weather: str = kwargs.get("weather", "clear")

        sun_direction, sun_intensity = self._get_sun_parameters(time, direction, weather)
        sun_color, ambient_color = self._calculate_sun_and_ambient([0, 0, 0], np.array(sun_direction), np.array(sun_intensity))
        # sun_color = self.apply_hdr_pipeline(sun_color, ev100=15.0)
        # ambient_color = self.apply_hdr_pipeline(ambient_color, ev100=15.0)
        PipelineManager.set_uniform_value("sw_SunIntensity", struct.pack('3f', sun_intensity, sun_intensity, sun_intensity))# 100, 100, 100))
        PipelineManager.set_uniform_value("sw_SunDirection", struct.pack('3f', *sun_direction))
        PipelineManager.set_uniform_value("sw_LightColor", struct.pack('3f', *sun_color))
        PipelineManager.set_uniform_value("sw_AmbientColor", struct.pack('3f', ambient_color[0] - 0.02, ambient_color[1] - 0.02, ambient_color[2] - 0.02))

        if self._scene:
           PipelineManager.process_cubemaps([self], "SkyBox")

        PipelineManager.import_resource("sw_Skybox", self._cubemap) # type: ignore

    @property
    def scene(self):
        return self._scene

    @scene.setter
    def scene(self, value: Scene):
        self._scene = value

    @property
    def resolution(self) -> int:
        return self._resolution

    @resolution.setter
    def resolution(self, value: int) -> None:
        self._resolution = value

    @property
    def target(self) -> Any:
        return self._target

    @target.setter
    def target(self, value: Any) -> None:
        self._target = value