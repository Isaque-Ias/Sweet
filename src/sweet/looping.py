import glfw
import moderngl_window as mglw
from moderngl_window.timers.clock import Timer
from moderngl_window.context.base import BaseWindow
from moderngl_window.context.base.keys import BaseKeys, KeyModifiers

from pathlib import Path
from .graphics.shaders import ShaderRender, ShaderManager
from .entity import EntityManager, Draw
from .inputting import Input
from PIL import Image
from typing import Literal, cast

_from_string_format = Literal["P", "RGB", "RGBX", "RGBA", "ARGB", "BGRA"]
delta_time = 0

class EngineWindow:
    def __init__(self, title: str="[Sem Nome]", size: tuple[int, int]=(1280, 720), fullscreen: bool=False, borderless: bool=False, resizable: bool = False, color: tuple[float, float, float, float]=(0, 0, 0, 1), samples: int=4):
        window_cls = mglw.get_window_cls('moderngl_window.context.glfw.Window')
        self.wnd = window_cls(
            title=title,
            gl_version=(3, 3),
            size=size,
            resizable=resizable,
            fullscreen=fullscreen,
            samples=samples,
            borderless=borderless,
            vsync=False
        )
        
        self.color = color
        self.ctx = self.wnd.ctx
        self.keys: BaseKeys = cast(BaseKeys, self.wnd.keys)
        Input.key_code = self.keys
        
        self.wnd.resize_func = self._on_resize
        self.wnd.key_event_func = self._on_key_event
        self.wnd.mouse_press_event_func = self._on_mouse_press
        self.wnd.mouse_release_event_func = self._on_mouse_release
        self.wnd.mouse_position_event_func = self._on_mouse_move
        self.wnd.mouse_scroll_event_func = self._on_mouse_scroll
        
        glfw.set_window_focus_callback(self.wnd._window, self._on_focus_change) # type: ignore

        mglw.activate_context(window=self.wnd)
        
        self.timer = Timer()
        self.timer.start()

    @property
    def size(self):
        return self.wnd.size

    @size.setter
    def size(self, value: tuple[int, int]):
        self.wnd.size = value

    @property
    def position(self):
        return self.wnd.position

    @position.setter
    def position(self, value: tuple[int, int]):
        self.wnd.position = value

    def toggle_fullscreen(self):
        self.wnd.fullscreen = not self.wnd.fullscreen

    def toggle_cursor(self):
        self.wnd.cursor = not self.wnd.cursor

    def center(self):
        monitor = glfw.get_primary_monitor()
        if not monitor:
            return
            
        video_mode = glfw.get_video_mode(monitor) # type: ignore
        screen_w = video_mode.size.width
        screen_h = video_mode.size.height
        
        win_w, win_h = self.size
        self.position = ((screen_w - win_w) // 2, (screen_h - win_h) // 2)

    def _on_mouse_press(self, x: int, y: int, button: int):
        Input.process_mouse_button_event(button, self.keys.ACTION_PRESS, self.keys)

    def _on_mouse_release(self, x: int, y: int, button: int):
        Input.process_mouse_button_event(button, self.keys.ACTION_RELEASE, self.keys)

    def _on_resize(self, width: int, height: int):
        self.ctx.viewport = (0, 0, width, height)

    def _on_mouse_move(self, x: int, y: int, dx: int, dy: int):
        Input.set_mouse_pos(x, y)
        pass

    def _on_key_event(self, key: int, action: int, modifiers: KeyModifiers):
        Input.process_key_event(key, action, self.keys)

        if action == self.keys.ACTION_PRESS:
            if key == self.keys.CAPS_LOCK:
                Input.set_caps(not Input.get_caps())

    def _on_mouse_scroll(self, x_offset: float, y_offset: float):
        Input.mouse_scroll_x = x_offset
        Input.mouse_scroll_y = y_offset

    def _on_focus_change(self, window: BaseWindow, has_focus: int):
        Input.set_focus(True if has_focus else False)

    def run(self):
        self.center()

        TICK_PER_SECOND = 60
        DELTA_TIME = 1.0 / TICK_PER_SECOND

        accumulator = 0.0
        
        while not self.wnd.is_closing:
            #current, delta
            _, delta_time = self.timer.next_frame()
            
            accumulator += delta_time

            while accumulator >= DELTA_TIME:
                self.update(DELTA_TIME)
                accumulator -= DELTA_TIME

            self.ctx.clear(*self.color)
            
            self.render()
            
            self.wnd.swap_buffers()
            
        self.wnd.destroy()
        
    def update(self, dt: float):
        global delta_time
        delta_time = dt
        entities = EntityManager.get_tick_entities(0)
        for entity in entities:
            entities[entity].pre_tick()
        entities = EntityManager.get_tick_entities(1)
        for entity in entities:
            entities[entity].tick()
        entities = EntityManager.get_tick_entities(2)
        for entity in entities:
            entities[entity].pos_tick()
              
        entity_changes = EntityManager.get_entity_changes()
        for key in entity_changes:
            EntityManager.create_entity(*entity_changes[key])

        destroy_changes = EntityManager.get_destroy_changes()
        for key in destroy_changes.keys():
            EntityManager.destroy_entity(destroy_changes[key])

        EntityManager.clear_agend()

    def render(self):
        if not ShaderManager.get_current_shader().name == "__def__":
            Draw.set_state_shader("__def__")

        entities = EntityManager.get_all_entities()
        for entity in entities.values():
            entity.draw()

        ShaderRender.render()

def get_window_data() -> tuple[int, int]:
    if glfw.init():
        monitor = glfw.get_primary_monitor()
        if monitor:
            video_mode = glfw.get_video_mode(monitor) # type: ignore
            
            view_width: int = video_mode.size.width
            view_height: int = video_mode.size.height
        else:
            view_width, view_height = 1280, 720
            
        glfw.terminate()
    else:
        view_width, view_height = 1280, 720
    return view_width, view_height

class GameLoop:
    _title: str = "[Sem Nome]"
    _non_full_screen_size: tuple[int, int] = (100, 100)
    _color: tuple[float, float, float, float] = (0, 0, 0, 0)
    fps: int = 60
    view_width, view_height = get_window_data()
    _fullscreen: bool = False
    _resizable: bool = True
    _borderless: bool = False
    _fullscreenable: bool = False
    _built = False
    debug: bool = False
    debug_time: bool = False
    _gl_version = (3, 3)
    _game_window: EngineWindow

    @classmethod
    def set_can_fullscreen(cls, value: bool) -> None:
        cls._fullscreenable = value

    @classmethod
    def get_can_fullscreen(cls) -> bool:
        return cls._fullscreenable

    @classmethod
    def get_fullscreen(cls) -> bool:
        return cls._fullscreen
    
    @classmethod
    def set_fullscreen(cls, value: bool) -> None:
        cls._fullscreen = value
        if cls._fullscreen:
            cls._screen_size = (cls.view_width, cls.view_height)

    @classmethod
    def set_resizable(cls, value: bool) -> None:
        cls._resizable = value

    @classmethod
    def get_resizable(cls) -> bool:
        return cls._resizable

    @classmethod
    def set_title(cls, title: str) -> None:
        cls._title = title

    @classmethod
    def set_fps(cls, fps: int) -> None:
        cls._fps = fps

    @classmethod
    def get_fps(cls) -> int:
        return cls._fps

    @classmethod
    def get_title(cls) -> str:
        return cls._title

    @classmethod
    def set_background_color(cls, color: tuple[float, float, float, float]) -> None:
        cls._color = (color[0] / 255, color[1] / 255, color[2] / 255, color[3] / 255)

    @classmethod
    def get_background_color(cls) -> tuple[float, float, float, float]:
        return cls._color

    @classmethod
    def set_screen_size(cls, size: tuple[int, int]) -> None:
        if not cls.get_fullscreen():
            cls._screen_size = size
        if size == (cls.view_width, cls.view_height):
            cls.set_fullscreen(True)

    @classmethod
    def get_screen_size(cls) -> tuple[int, int]:
        return cls._screen_size
    
    @classmethod
    def init(cls) -> None:
        window = EngineWindow(
            title=cls._title, 
            size=cls._screen_size, 
            fullscreen=cls._fullscreen,
            borderless=cls._borderless,
            resizable=cls._resizable,
            color=cls._color,
            samples=4
        )

        cls._game_window = window
        glfw.focus_window(window.wnd._window) # type: ignore
        Input.wnd = window.wnd
        
        BASE_DIR = Path(__file__).resolve().parent
        BUILD = BASE_DIR / "build"
        ShaderManager.set_context(window.ctx)
        ShaderManager.add_shader("__def__", BUILD / "__sh__.vsh", BUILD / "__sh__.fsh")
        cls._built = True

    @classmethod
    def end(cls) -> None:
        cls._running = False

    @classmethod
    def start(cls) -> None:
        cls._fps = 60

        cls._game_window.run()

if __name__ == "__main__":
    GameLoop.start()