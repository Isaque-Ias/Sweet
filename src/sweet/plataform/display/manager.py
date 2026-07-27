from abc import ABC, abstractmethod
from enum import Enum, auto

class DisplayTypes(Enum):
    GLFW = auto()

class Display(ABC):
    def __init__(self, type: DisplayTypes):
        self.display_type = type
        DisplayManager.add_display(self)

    @abstractmethod
    def is_showing(self) -> bool:
        pass

class DisplayManager:
    _displays: list[Display] = []
    run_id: int = 0

    @classmethod
    def get_active_displays(cls) -> list[Display]:
        actives: list[Display] = []
        for display in cls._displays:
            if display.is_showing():
                actives.append(display)
                
        return actives

    @classmethod
    def add_display(cls, display: Display) -> int:
        if not display in cls._displays:
            cls._displays.append(display)
            cls.run_id += 1
            return cls.run_id

        return -1