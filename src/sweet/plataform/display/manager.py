from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any
from ..hal.manager import RenderTarget

class DisplayTypes(Enum):
    GLFW = auto()

class DisplaySurface(ABC):
    @abstractmethod
    def initialize(self, width: int, height: int, title: str):
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass

    @abstractmethod
    def poll_events(self) -> bool:
        pass

    @abstractmethod
    def swap_buffers(self):
        pass

    @abstractmethod
    def get_native_handle(self) -> Any:
        pass

    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def size(self) -> tuple[int, int]:
        pass

    @property
    @abstractmethod
    def should_close(self) -> bool:
        pass

    @property
    @abstractmethod
    def render_target(self) -> RenderTarget:
        pass

class DisplayManager:
    _displays: list[DisplaySurface] = []
    run_id: int = 0

    @classmethod
    def query_displays(cls) -> list[DisplaySurface]:
        actives: list[DisplaySurface] = []
        for display in cls._displays:
            if display.is_active():
                actives.append(display)
                
        return actives

    @classmethod
    def add_display(cls, display: DisplaySurface) -> int:
        if not display in cls._displays:
            cls._displays.append(display)
            cls.run_id += 1
            return cls.run_id

        return -1