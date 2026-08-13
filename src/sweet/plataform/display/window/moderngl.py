from sweet.core import system
import moderngl_window as mglw
from moderngl_window.context.base import BaseWindow
from ...inputs.window_input import WindowInput
from typing import Any, Optional
from ..manager import DisplayManager
from .window import WindowSurface
from ...hal.manager import GraphicsDevice, RenderTarget
from ...hal.opengl.mgl import ModernGLWindowTarget
import glfw
import moderngl_window as mglw
from moderngl_window.context.base import BaseWindow
from moderngl_window.context.glfw.keys import Keys as GLFWKeys

class _SecondaryWindowProxy:
    _is_proxy = True
    keys = GLFWKeys
    
    def __init__(self, glfw_handle: Any, size: tuple[int, int], title: str):
        self._window = glfw_handle
        self._size = size
        self._title = title
        self._cursor = True
        self._mouse_exclusivity = False
        self._fullscreen = False

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    @fullscreen.setter
    def fullscreen(self, value: bool):
        self._fullscreen = value
        if self._window:
            monitor = glfw.get_primary_monitor()
            if monitor:
                mode = glfw.get_video_mode(monitor) # type: ignore
                if mode:
                    if value:
                        glfw.set_window_monitor( # type: ignore
                            self._window, monitor, 0, 0, mode.size.width, mode.size.height, mode.refresh_rate
                        )
                    else:
                        w, h = self._size
                        glfw.set_window_monitor(self._window, None, 100, 100, w, h, 0) # type: ignore

    @property
    def size(self) -> tuple[int, int]:
        if self._window:
            return glfw.get_window_size(self._window) # type: ignore
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]):
        self._size = value
        if self._window:
            glfw.set_window_size(self._window, value[0], value[1]) # type: ignore

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value
        if self._window:
            glfw.set_window_title(self._window, value) # type: ignore

    @property
    def position(self) -> tuple[int, int]:
        if self._window:
            return glfw.get_window_pos(self._window) # type: ignore
        return (0, 0)

    @position.setter
    def position(self, value: tuple[int, int]):
        if self._window:
            glfw.set_window_pos(self._window, value[0], value[1]) # type: ignore

    @property
    def cursor(self) -> bool:
        return self._cursor

    @cursor.setter
    def cursor(self, value: bool):
        self._cursor = value
        if self._window:
            mode = glfw.CURSOR_NORMAL if value else glfw.CURSOR_HIDDEN
            glfw.set_input_mode(self._window, glfw.CURSOR, mode) # type: ignore

    @property
    def mouse_exclusivity(self) -> bool:
        return self._mouse_exclusivity

    @mouse_exclusivity.setter
    def mouse_exclusivity(self, value: bool):
        self._mouse_exclusivity = value
        if self._window:
            mode = glfw.CURSOR_DISABLED if value else glfw.CURSOR_NORMAL
            glfw.set_input_mode(self._window, glfw.CURSOR, mode) # type: ignore

    def get_native_handle(self) -> Any:
        if self.wnd and hasattr(self.wnd, "_window"):
            return self.wnd._window  # type: ignore
        return None

    def swap_buffers(self):
        if self._window:
            glfw.swap_buffers(self._window) # type: ignore

    def destroy(self):
        if self._window:
            glfw.destroy_window(self._window)  # type: ignore
            self._window = None

    def close(self):
        if self._active:
            self._active = False
            self._should_close = True

            handle = self.get_native_handle()
            if handle:
                glfw.destroy_window(handle)  # type: ignore

            if mglw.context.CURRENT_WINDOW == self.wnd:  # type: ignore
                mglw.context.CURRENT_WINDOW = None  # type: ignore

            self.wnd = None
            self._offscreen_target = None

    def make_current(self):
        handle = self.get_native_handle()
        if handle:
            glfw.make_context_current(handle) # type: ignore

    def poll_events(self) -> bool:
        if not self._active:
            return False

        handle = self.get_native_handle()
        if handle:
            glfw.poll_events()
            if glfw.window_should_close(handle): # type: ignore
                self._should_close = True

        return not self._should_close

class GLWindow(WindowSurface):
    _PRIMARY_WINDOW_HANDLE: Any = None

    def __init__(
        self,
        graphics_device: GraphicsDevice,
        title: str = "Window",
        size: tuple[int, int] = (1280, 720),
        position: Optional[tuple[int, int]] = None,
        fullscreen: bool = False,
        resizable: bool = True,
        pixel_samples: int = 4
    ):
        DisplayManager.add_display(self)

        self.graphics_device = graphics_device
        self._offscreen_target: Optional[RenderTarget] = None
        self._backbuffer_target = ModernGLWindowTarget(self)
    
        self._title = title
        self._size = size
        self._position = position
        self._fullscreen = fullscreen
        self._resizable = resizable
        self._pixel_samples = pixel_samples

        self._active = False
        self._should_close = False
        
        self.wnd: Optional[BaseWindow] = None

        self.input_manager = WindowInput(self) # type: ignore

    def make_current(self):
        if self.wnd:
            glfw.make_context_current(self.wnd._window) # type: ignore

    def initialize(self, width: int, height: int, title: str):
        self._size = (width, height)
        self._title = title

        if GLWindow._PRIMARY_WINDOW_HANDLE is None:
            raise RuntimeError(
                "Engine em OpenGL falhou"
                "Engine precisa inicializar contexto dummy"
            )

        try:
            glfw.window_hint(glfw.VISIBLE, glfw.TRUE) # type: ignore
            glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4) # type: ignore
            glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6) # type: ignore
            glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE) # type: ignore
            glfw.window_hint(glfw.RESIZABLE, glfw.TRUE if self._resizable else glfw.FALSE) # type: ignore
            glfw.window_hint(glfw.SAMPLES, self._pixel_samples) # type: ignore

            raw_handle = glfw.create_window( # type: ignore
                width, height, title, None, GLWindow._PRIMARY_WINDOW_HANDLE
            )
            if not raw_handle:
                raise RuntimeError(f"Janela falhou para inicializar: {title}")

            glfw.make_context_current(raw_handle) # type: ignore

            primary_handle = GLWindow._PRIMARY_WINDOW_HANDLE
            if primary_handle is None and hasattr(self.graphics_device, "_dummy_window"):
                primary_handle = self.graphics_device._dummy_window # type: ignore

            if hasattr(self, '_use_mglw_proxy') and self._use_mglw_proxy: # type: ignore
                window_cls = mglw.get_window_cls("moderngl_window.context.glfw.Window")

                self.wnd = window_cls(
                    title=self._title,
                    gl_version=(4, 6),
                    size=self._size,
                    resizable=self._resizable,
                    fullscreen=self._fullscreen,
                    samples=self._pixel_samples,
                    vsync=True,
                    ctx=self.graphics_device.ctx # type: ignore
                )

            else:
                self.wnd = _SecondaryWindowProxy(raw_handle, (width, height), title) # type: ignore

            self.input_manager.attach_input(self.wnd)

            if self._position and hasattr(self.wnd, 'position'):
                self.wnd.position = self._position # type: ignore

            self._create_offscreen_target(width, height)
            self._active = True

        except Exception as e:
            system.problem(f"Falha ao inicializar GLWindow: {e}")

    def _create_offscreen_target(self, width: int, height: int):
        if self._offscreen_target:
            self._offscreen_target.release() # type: ignore
            self._offscreen_target = None
            
        self._offscreen_target = self.graphics_device.create_mrt_framebuffer(
            width=max(width, 1),
            height=max(height, 1),
            color_formats=[4], # RGBA
            has_depth=True
        )

    def is_active(self) -> bool:
        return self._active

    @property
    def input(self) -> WindowInput:
        return self.input_manager

    @property
    def render_target(self) -> RenderTarget:
        if self._offscreen_target is None: # type: ignore
            raise RuntimeError("GLWindow não possui um RenderTarget offscreen válido")
        return self._offscreen_target

    def poll_events(self) -> bool:
        if not self.wnd or not self._active:
            return False

        handle = self.get_native_handle()
        if handle:
            if glfw.window_should_close(handle): # type: ignore
                self._should_close = True
            
            current_w, current_h = glfw.get_window_size(handle) # type: ignore
            if (current_w, current_h) != self._size and current_w > 0 and current_h > 0:
                self._size = (current_w, current_h)
                self._create_offscreen_target(current_w, current_h)

        return not self._should_close
    
    def swap_buffers(self):
        if self.wnd and self._offscreen_target:
            self.make_current()

            self.graphics_device.blit_texture_to_target(
                src_target=self._offscreen_target,
                dst_target=self._backbuffer_target
            )

            self.wnd.swap_buffers()

    def get_native_handle(self) -> Any:
        if self.wnd and hasattr(self.wnd, "_window"):
            return self.wnd._window # type: ignore
        return None

    def close(self):
        if self._active:
            self._active = False
            self._should_close = True

            if self._offscreen_target:
                if hasattr(self._offscreen_target, 'release'):
                    self._offscreen_target.release() # type: ignore
                self._offscreen_target = None

            if self.wnd and hasattr(self.wnd, "_window") and self.wnd._window: # type: ignore
                glfw.destroy_window(self.wnd._window) # type: ignore

            mglw.context.CURRENT_WINDOW = None # type: ignore
            self.wnd = None

    @property
    def should_close(self) -> bool:
        return self._should_close

    # window specific
    
    def _apply_title(self, title: str) -> None:
        if self.wnd:
            self.wnd.title = title

    def _apply_size(self, width: int, height: int) -> None:
        if self.wnd:
            self.wnd.size = (width, height)
        self._size = (width, height)
        self._create_offscreen_target(width, height)

    def _apply_position(self, x: int, y: int) -> None:
        if self.wnd and hasattr(self.wnd, 'position'):
            self.wnd.position = (x, y)

    def _apply_fullscreen(self, enable: bool) -> None:
        self._fullscreen = enable
        if self.wnd:
            self.wnd.fullscreen = enable
            
            handle = self.get_native_handle()
            if handle:
                w, h = glfw.get_window_size(handle) # type: ignore
                self._apply_size(w, h)

    @property
    def cursor_visible(self) -> bool:
        if self.wnd:
            return self.wnd.cursor
        return True

    @cursor_visible.setter
    def cursor_visible(self, value: bool):
        if self.wnd:
            self.wnd.cursor = value

    @property
    def mouse_exclusivity(self) -> bool:
        if self.wnd:
            return self.wnd.mouse_exclusivity
        return False

    @mouse_exclusivity.setter
    def mouse_exclusivity(self, value: bool):
        if self.wnd:
            self.wnd.mouse_exclusivity = value

    def center_on_screen(self):
        monitor = glfw.get_primary_monitor()
        if not monitor:
            return

        video_mode = glfw.get_video_mode(monitor) # type: ignore
        if video_mode:
            screen_w = video_mode.size.width
            screen_h = video_mode.size.height
            win_w, win_h = self.size
            self.position = ((screen_w - win_w) // 2, (screen_h - win_h) // 2)