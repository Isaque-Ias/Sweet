from abc import ABC, abstractmethod
from typing import Optional
from ..manager import DisplaySurface
from ...hal.manager import GraphicsDevice, RenderTarget

class WindowSurface(DisplaySurface, ABC):
    def __init__(
        self,
        graphics_device: GraphicsDevice,
        title: str = "Application Window",
        size: tuple[int, int] = (1280, 720),
        position: Optional[tuple[int, int]] = None
    ):
        super().__init__()
        self.graphics_device = graphics_device
        self._title = title
        self._size = size
        self._position = position
        self._scale: tuple[float, float] = (1.0, 1.0)
        self._fullscreen: bool = False
        self._active: bool = False
        self._should_close: bool = False

    # --- win methods

    @abstractmethod
    def make_current(self):
        pass

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value
        if self._active:
            self._apply_title(value)

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def render_target(self) -> RenderTarget:
        return self.render_target

    @size.setter
    def size(self, value: tuple[int, int]):
        self._size = value
        if self._active:
            self._apply_size(value[0], value[1])

    @property
    def position(self) -> Optional[tuple[int, int]]:
        return self._position

    @position.setter
    def position(self, value: tuple[int, int]):
        self._position = value
        if self._active:
            self._apply_position(value[0], value[1])

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    @fullscreen.setter
    def fullscreen(self, value: bool):
        self._fullscreen = value
        if self._active:
            self._apply_fullscreen(value)

    @property
    def should_close(self) -> bool:
        return self._should_close

    @abstractmethod
    def _apply_title(self, title: str) -> None:
        pass

    @abstractmethod
    def _apply_size(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    def _apply_position(self, x: int, y: int) -> None:
        pass

    @abstractmethod
    def _apply_fullscreen(self, enable: bool) -> None:
        pass