from typing import Any, Optional
from moderngl_window.context.base import BaseWindow
from sweet.plataform.display.manager import DisplaySurface
from sweet.plataform.inputs.window_input import WindowInput
from ...hal.manager import GraphicsDevice, RenderTarget

class GLWindow(DisplaySurface):
    background_color: tuple[float, float, float, float]
    title: str
    focus: bool
    mouse_exclusivity: bool
    cursor: bool
    resizable: bool
    position: tuple[int, int]
    fullscreen: bool
    config: dict[str, Any]
    wnd: BaseWindow | None = None

    @property
    def size(self) -> tuple[int, int]: ...

    @property
    def render_target(self) -> RenderTarget: ...

    @property
    def should_close(self) -> bool: ...

    def make_current(self) -> None: ...

    def is_active(self) -> bool: ...

    def initialize(self, width: int, height: int, title: str) -> None: ...

    def poll_events(self) -> bool: ...

    def swap_buffers(self) -> None: ...

    def get_native_handle(self) -> Any: ...

    def close(self) -> None: ...

    @property
    def input(self) -> WindowInput: ...

    def __init__(
            self,
            graphics_device: GraphicsDevice,
            title: str = "Window",
            size: tuple[int, int] = (1280, 720),
            position: Optional[tuple[int, int]] = None,
            fullscreen: bool = False,
            resizable: bool = True,
            pixel_samples: int = 4) -> None: ...

