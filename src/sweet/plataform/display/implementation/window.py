import glfw
import moderngl_window as mglw
from moderngl_window.context.base import BaseWindow
from ...inputs.window_input import WindowInput
from ....core import system
from ...renderer.render_device import GLContext
from typing import Any, cast, Callable
from ..manager import Display, DisplayTypes
import sweet

class Window(Display):
    def __init__(
        self,
        title: str = "[Sem Nome]",
        size: tuple[int, int] | None = None,
        position: tuple[int, int] | None = None,
        fullscreen: bool = False,
        resizable: bool = False,
        background_color: tuple[float, float, float, float] = (0, 0, 0, 1),
        pixel_samples: int = 4):

        super().__init__(DisplayTypes.GLFW)

        self._title = title
        self._position = position
        self._size = size
        self._fullscreen = fullscreen
        self._resizable = resizable
        self._pixel_samples = pixel_samples
        self._background_color = background_color

        self._active = False

        self.wnd: BaseWindow | None = None
        
        # O cast força o Pylance a converter o 'self' incompleto para o TargetWindow esperado
        self.input_manager: WindowInput = WindowInput(cast("sweet.plataform.display.implementation.window.Window", self))

        self._config: dict[str, Any] = {
            "title": title,
            "size": size,
            "position": position,
            "fullscreen": fullscreen,
            "resizable": resizable,
            "background_color": size,
            "samples": pixel_samples,
        }

        self.running = False

    def is_showing(self):
        return self._active

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, color: tuple[float, float, float, float]):
        self._background_color = color

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        if self.wnd:
            self.wnd.title = value
            
        self._title = value
    
    @property
    def focus(self):
        if self.wnd:
            return glfw.get_window_attrib(self.wnd._window, glfw.FOCUSED) # type: ignore

    @focus.setter
    def focus(self, value: bool):
        if self.wnd:
            gl_bool = glfw.FALSE
            if value: 
                gl_bool = glfw.TRUE
            glfw.get_window_attrib(self.wnd._window, glfw.FOCUSED, gl_bool) # type: ignore

    @property
    def cursor(self):
        if self.wnd:
            return self.wnd.cursor

    @cursor.setter
    def cursor(self, value: bool):
        if self.wnd:
            self.wnd.cursor = value

    @property
    def mouse_exclusivity(self):
        if self.wnd:
            return self.wnd.mouse_exclusivity

    @mouse_exclusivity.setter
    def mouse_exclusivity(self, value: bool):
        if self.wnd:
            self.wnd.mouse_exclusivity = value

    @property
    def resizable(self):
        return self._resizable

    @resizable.setter
    def resizable(self, value: bool):
        if self._active:
            gl_bool = glfw.FALSE
            if value: 
                gl_bool = glfw.TRUE
            glfw.set_window_attrib(self.wnd._window, glfw.RESIZABLE, gl_bool) # type: ignore
            
        self._resizable = value

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]):
        if self.wnd:
            self.wnd.size = value

        self._size = value

    @property
    def fullscreen(self):
        return self._fullscreen

    @fullscreen.setter
    def fullscreen(self, value: bool):
        if self.wnd:
            self.wnd.fullscreen = value

        self._fullscreen = value

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value: tuple[int, int]):
        if self.wnd:
            self.wnd.position = value

        self._position = value

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value: dict[str, Any]):
        if "size" in value:
            self.size = value["size"]
            self._config["size"] = value

        if "position" in value:
            self.position = value["position"]
            self._config["position"] = value

        if "title" in value:
            self.title = value["title"]
            self._config["title"] = value

        if "resizable" in value:
            self.resizable = value["resizable"]
            self._config["resizable"] = value

        if "background_color" in value:
            self.background_color = value["background_color"]
            self._config["background_color"] = value

        if "fullscreen" in value:
            self.fullscreen = value["fullscreen"]
            self._config["fullscreen"] = value

    def center(self):
        if self._size is None:
            system.warn("Não há como centralizar antes de definir o tamanho da janela")
            return

        monitor = glfw.get_primary_monitor()
        if not monitor:
            return

        video_mode = glfw.get_video_mode(monitor)  # type: ignore
        screen_w = video_mode.size.width
        screen_h = video_mode.size.height

        win_w, win_h = self._size
        self.position = ((screen_w - win_w) // 2, (screen_h - win_h) // 2)

    def show(self, focus: bool = True):
        if not self._active:
            try:
                window_cls = mglw.get_window_cls("moderngl_window.context.glfw.Window")

                if not GLContext.has_context():
                    GLContext.use_context()
                
                ctx = GLContext.get_context()
                
                self.wnd = window_cls(
                    title=self._title,
                    gl_version=(3, 3),
                    size=self._size or (1280, 720),
                    resizable=self._resizable,
                    fullscreen=self._fullscreen,
                    samples=self._pixel_samples,
                    vsync=True,
                    ctx=ctx
                )
        
                monitor = glfw.get_primary_monitor()
        
                video_mode = glfw.get_video_mode(monitor)  # type: ignore
                screen_w = video_mode.size.width
                screen_h = video_mode.size.height
        
                if self._size is None:
                    if not monitor:
                        self._size = (720, 1280)
                    else:
                        self._size = (screen_w, screen_h)
        
                if self._position is None:
                    win_w, win_h = self._size
                    self._position = ((screen_w - win_w) // 2, (screen_h - win_h) // 2)

                self.size = self._size
                self.position = self._position
                    
                self.input_manager.attach_input()

                mglw.activate_context(window=self.wnd)

                if focus:
                    glfw.focus_window(self.wnd._window)  # type: ignore
                
                self._active = True
            except Exception as e:
                system.problem(f"Falha ao exibir janela: {e}")

    def close(self):
        if self._active:
            self._active = False

            self.input_manager.dettach_input()

            if hasattr(self, 'ctx') and self.ctx:
                try:
                    self.ctx.release()
                except Exception:
                    pass
                self.ctx = None

            if hasattr(self, 'wnd') and self.wnd and self.wnd._window: # type: ignore
                glfw.destroy_window(self.wnd._window) # type: ignore
                
            import moderngl_window as mglw
            mglw.context.CURRENT_WINDOW = None # type: ignore
        
            self.wnd = None

    def draw(self, operation: Callable[..., Any]):
        if self.wnd:
            glfw.make_context_current(self.wnd._window) # type: ignore
            self.wnd.ctx.clear(*self._background_color)
            operation()
            self.wnd.swap_buffers()