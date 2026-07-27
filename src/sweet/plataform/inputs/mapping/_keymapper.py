from __future__ import annotations
import glfw
from .input_codes import Key, MouseButton
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...display.implementation.window import Window

class GenericMapper(ABC):
    @abstractmethod
    def to_sweet_key(self, key: int) -> Key:
        pass

    @abstractmethod
    def to_sweet_mouse(self, button: int) -> MouseButton:
        pass

class GlfwKeyMapper(GenericMapper):
    def __init__(self):
        pass

    def set_keys(self, window: Window):
        if not window.wnd:
            raise AttributeError("Mapeador GLFW precisa que a janela esteja instanciada")
        self.base_keys = window.wnd.keys
        
        self._KEY_MAP: dict[int, Key] = {
            self.base_keys.A: Key.A,
            self.base_keys.B: Key.B,
            self.base_keys.SPACE: Key.SPACE,
            self.base_keys.ESCAPE: Key.ESCAPE,
            self.base_keys.CAPS_LOCK: Key.CAPS_LOCK,
        }

        self._MOUSE_MAP: dict[int, MouseButton] = {
            glfw.MOUSE_BUTTON_LEFT: MouseButton.LEFT,
            glfw.MOUSE_BUTTON_RIGHT: MouseButton.RIGHT,
        }

    def to_sweet_key(self, key: int) -> Key:
        return self._KEY_MAP.get(key, Key.UNDEFINED)

    def to_sweet_mouse(self, button: int) -> MouseButton:
        return self._MOUSE_MAP.get(button, MouseButton.UNDEFINED)