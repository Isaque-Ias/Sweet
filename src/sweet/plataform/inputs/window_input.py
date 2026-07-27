from __future__ import annotations
import glfw
from moderngl_window.context.base.keys import KeyModifiers
from .periferic.keyboard import KeyboardInput
from .periferic.mouse import MouseInput
from .common import ActionState
from .periferic.interface import KeyboardInterface, MouseInterface
from .mapping._keymapper import GlfwKeyMapper
import sweet

class WindowInput(KeyboardInterface, MouseInterface):
    def __init__(self, window: "sweet.plataform.display.implementation.window.Window"):
        self.window = window
        self._keyboard = KeyboardInput()
        self._mouse = MouseInput()
        self._key_mapper = GlfwKeyMapper()
        KeyboardInterface.__init__(self, self._keyboard)
        MouseInterface.__init__(self, self._mouse)

    def _on_mouse_press(self, x: int, y: int, button: int):
        if self.window.wnd:
            self._mouse.process_mouse_event(button, ActionState.PRESS, self._key_mapper)

    def _on_mouse_release(self, x: int, y: int, button: int):
        if self.window.wnd:
            self._mouse.process_mouse_event(button, ActionState.RELEASE, self._key_mapper)

    def _on_resize(self, width: int, height: int):
        if self.window.wnd:
            self.window.wnd.ctx.viewport = (0, 0, width, height)

    def _on_mouse_move(self, x: int, y: int, dx: int, dy: int):
        self._mouse.update_mouse_pos(x, y)
        self._mouse.update_mouse_delta(dx, dy)

    def _on_key_event(self, key: int, action: int, modifiers: KeyModifiers):
        if self.window.wnd:
            if action == self.window.wnd.keys.ACTION_PRESS:
                self._keyboard.process_key_event(key, ActionState.PRESS, self._key_mapper)
            elif action == self.window.wnd.keys.ACTION_PRESS:
                self._keyboard.process_key_event(key, ActionState.RELEASE, self._key_mapper)

    def _on_mouse_scroll(self, x_offset: float, y_offset: float):
        self._mouse.mouse_scroll_x = x_offset
        self._mouse.mouse_scroll_y = y_offset

    def attach_input(self):
        if self.window.wnd:
            self.window.wnd.resize_func = self._on_resize
            self.window.wnd.key_event_func = self._on_key_event
            self.window.wnd.mouse_press_event_func = self._on_mouse_press
            self.window.wnd.mouse_release_event_func = self._on_mouse_release
            self.window.wnd.mouse_position_event_func = self._on_mouse_move
            self.window.wnd.mouse_scroll_event_func = self._on_mouse_scroll
            self._key_mapper.set_keys(self.window)

    def dettach_input(self):
        if hasattr(self, 'wnd') and self.window.wnd:
            if self.window.wnd._window: # type: ignore
                glfw.set_window_focus_callback(self.window.wnd._window, None) # type: ignore
            
            self.window.wnd.resize_func = None
            self.window.wnd.key_event_func = None
            self.window.wnd.mouse_press_event_func = None
            self.window.wnd.mouse_release_event_func = None
            self.window.wnd.mouse_position_event_func = None
            self.window.wnd.mouse_scroll_event_func = None