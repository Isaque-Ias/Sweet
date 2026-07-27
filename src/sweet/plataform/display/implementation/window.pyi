from typing import Any, Callable
from moderngl_window.context.base import BaseWindow

class Window:
    is_showing: bool
    background_color: tuple[float, float, float, float]
    title: str
    focus: bool
    mouse_exclusivity: bool
    cursor: bool
    size: tuple[int, int]
    resizable: bool
    position: tuple[int, int]
    fullscreen: bool
    config: dict[str, Any]
    wnd: BaseWindow | None = None

    def __init__(
            self,
            title: str = "[Sem Nome]",
            size: tuple[int, int] | None = None,
            position: tuple[int, int] | None = None,
            fullscreen: bool = False,
            resizable: bool = False,
            background_color: tuple[float, float, float, float] = (0, 0, 0, 1),
            pixel_samples: int = 4) -> None: ...

    def show(self) -> None: ...
    def close(self) -> None: ...
    def draw(self, op: Callable[..., None]) -> None: ...