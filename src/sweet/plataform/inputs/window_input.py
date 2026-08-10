from __future__ import annotations
import glfw
from moderngl_window.context.base.keys import KeyModifiers
from .periferic.keyboard import KeyboardInput
from .periferic.mouse import MouseInput
from .common import ActionState
from .periferic.interface import KeyboardInterface, MouseInterface
from .mapping._keymapper import GlfwKeyMapper
from typing import Any

class WindowInput(KeyboardInterface, MouseInterface):
    def __init__(self, window: Any):
        self.window = window
        self._keyboard = KeyboardInput()
        self._mouse = MouseInput()
        self._key_mapper = GlfwKeyMapper()
        KeyboardInterface.__init__(self, self._keyboard)
        MouseInterface.__init__(self, self._mouse)

    def get_mouse_delta(self) -> tuple[int, int]:
        return self._mouse.get_mouse_delta()

    def get_mouse_pos(self) -> tuple[int, int]:
        return self._mouse.get_mouse_pos()

    def is_mouse_pressed(self, button: Any) -> bool:
        return self._mouse.is_mouse_pressed(button)

    def is_mouse_released(self, button: Any) -> bool:
        return self._mouse.is_mouse_released(button)

    def is_mouse_held(self, button: Any) -> bool:
        return self._mouse.is_mouse_held(button)

    @property
    def caps(self) -> bool:
        return self._keyboard.caps

    def is_key_pressed(self, key: Any) -> bool:
        return self._keyboard.is_key_pressed(key)

    def is_key_released(self, key: Any) -> bool:
        return self._keyboard.is_key_released(key)

    def is_key_held(self, key: Any) -> bool:
        return self._keyboard.is_key_held(key)

    # --- main ---

    def reset(self):
        self._mouse.reset()

    def _on_mouse_press(self, x: int, y: int, button: int):
        if self.window.wnd:
            self._mouse.process_mouse_event(button, ActionState.PRESS, self._key_mapper)

    def _on_mouse_release(self, x: int, y: int, button: int):
        if self.window.wnd:
            self._mouse.process_mouse_event(button, ActionState.RELEASE, self._key_mapper)

    def _on_resize(self, width: int, height: int):
        if self.wnd and hasattr(self.wnd, "ctx") and self.wnd.ctx:
            self.wnd.ctx.viewport = (0, 0, width, height)

    def _on_mouse_move(self, x: int, y: int, dx: int, dy: int):
        self._mouse.update_mouse_pos(x, y)
        self._mouse.update_mouse_delta(dx, dy)

    def _on_key_event(self, key: int, action: int, modifiers: KeyModifiers):
        if self.wnd:
            if action == self.wnd.keys.ACTION_PRESS:
                self._keyboard.process_key_event(key, ActionState.PRESS, self._key_mapper)
            elif action == self.wnd.keys.ACTION_RELEASE:
                self._keyboard.process_key_event(key, ActionState.RELEASE, self._key_mapper)

    def _on_mouse_scroll(self, x_offset: float, y_offset: float):
        self._mouse.mouse_scroll_x = x_offset
        self._mouse.mouse_scroll_y = y_offset

    # --- alt ---

    def _glfw_resize(self, window: Any, width: int, height: int):
        self._on_resize(width, height)

    def _glfw_key(self, window: Any, key: int, scancode: int, action: int, mods: KeyModifiers):
        self._on_key_event(key, action, mods)

    def _glfw_mouse_button(self, window: Any, button: int, action: int, mods: KeyModifiers):
        x, y = glfw.get_cursor_pos(window) # type: ignore
        if action == glfw.PRESS:
            self._on_mouse_press(int(x), int(y), button)
        elif action == glfw.RELEASE:
            self._on_mouse_release(int(x), int(y), button)

    def _glfw_cursor_pos(self, window: Any, xpos: float, ypos: float):
        # Retrieve or compute delta if needed by _on_mouse_move
        dx = xpos - getattr(self, "_last_x", xpos)
        dy = ypos - getattr(self, "_last_y", ypos)
        self._last_x, self._last_y = xpos, ypos

        self._on_mouse_move(int(xpos), int(ypos), int(dx), int(dy))

    def _glfw_scroll(self, window: Any, xoffset: float, yoffset: float):
        self._on_mouse_scroll(xoffset, yoffset)

    # --- attach ---

    def attach_input(self, wnd: Any):
        self.wnd = wnd
        if not wnd:
            return

        if not hasattr(wnd, "_is_proxy"):
            wnd.resize_func = self._on_resize
            wnd.key_event_func = self._on_key_event
            wnd.mouse_press_event_func = self._on_mouse_press
            wnd.mouse_release_event_func = self._on_mouse_release
            wnd.mouse_position_event_func = self._on_mouse_move
            wnd.mouse_scroll_event_func = self._on_mouse_scroll

        else:
            native_handle = self.window.get_native_handle()
            if native_handle:
                glfw.set_window_size_callback(native_handle, self._glfw_resize) # type: ignore
                glfw.set_key_callback(native_handle, self._glfw_key) # type: ignore
                glfw.set_mouse_button_callback(native_handle, self._glfw_mouse_button) # type: ignore
                glfw.set_cursor_pos_callback(native_handle, self._glfw_cursor_pos) # type: ignore
                glfw.set_scroll_callback(native_handle, self._glfw_scroll) # type: ignore

        self._key_mapper.set_keys(self.window)

    def dettach_input(self):
        if hasattr(self, 'wnd') and self.wnd:
            if self.wnd._window: # type: ignore
                glfw.set_window_focus_callback(self.wnd._window, None) # type: ignore
            
            self.wnd.resize_func = None
            self.wnd.key_event_func = None
            self.wnd.mouse_press_event_func = None
            self.wnd.mouse_release_event_func = None
            self.wnd.mouse_position_event_func = None
            self.wnd.mouse_scroll_event_func = None