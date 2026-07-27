from .keyboard import KeyboardInput
from .mouse import MouseInput
from .gamepad import GamepadInput
from ..mapping.input_codes import Key, MouseButton

class KeyboardInterface:
    def __init__(self, keyboard: KeyboardInput):
        self._keyboard = keyboard

    @property
    def caps(self):
        return self._keyboard.caps

    def is_key_pressed(self, key: Key) -> bool:
        return self._keyboard.is_key_pressed(key)

    def is_key_released(self, key: Key) -> bool:
        return self._keyboard.is_key_released(key)

    def is_key_held(self, key: Key) -> bool:
        return self._keyboard.is_key_held(key)

class MouseInterface:
    def __init__(self, mouse: MouseInput):
        self._mouse = mouse

    @property
    def mouse_delta(self) -> tuple[int, int]:
        return self._mouse.get_mouse_delta()

    @property
    def pos(self) -> tuple[int, int]:
        return self._mouse.get_mouse_pos()

    def is_mouse_pressed(self, button: MouseButton) -> bool:
        return self._mouse.is_mouse_pressed(button)

    def is_mouse_released(self, button: MouseButton) -> bool:
        return self._mouse.is_mouse_released(button)

    def is_mouse_held(self, button: MouseButton) -> bool:
        return self._mouse.is_mouse_held(button)
    
class GamepadInterface:
    def __init__(self, gamepad: GamepadInput):
        self._gamepad = gamepad
    