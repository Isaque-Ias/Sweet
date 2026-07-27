from dataclasses import dataclass
from ..common import ActionState
from ..mapping.input_codes import Key
from ..mapping._keymapper import GenericMapper

@dataclass
class KeyState:
    released: bool = False
    pressed: bool = False
    held: bool = False

class KeyboardInput:
    def __init__(self) -> None:
        self._keys: dict[Key, KeyState] = {}
        self._caps: bool = False

    def process_key_event(self, generic_key: int, action: ActionState, mapper: GenericMapper):
        key = mapper.to_sweet_key(generic_key)
        
        if key not in self._keys:
            self._keys[key] = KeyState()

        self._keys[key].pressed = False
        self._keys[key].released = False

        if action == ActionState.PRESS:
            if key == Key.CAPS_LOCK:
                self._caps = not self._caps

            if not self._keys[key].held:
                self._keys[key].pressed = True
            self._keys[key].held = True

        elif action == ActionState.RELEASE:
            if self._keys[key].held:
                self._keys[key].released = True
            self._keys[key].held = False

    @property
    def caps(self) -> bool:
        return self._caps

    def is_key_pressed(self, key: Key) -> bool:
        if self._keys.get(key) is None:
            self._keys[key] = KeyState()

        return self._keys[key].pressed

    def is_key_released(self, key: Key) -> bool:
        if self._keys.get(key) is None:
            self._keys[key] = KeyState()

        return self._keys[key].released

    def is_key_held(self, key: Key) -> bool:
        if self._keys.get(key) is None:
            self._keys[key] = KeyState()

        return self._keys[key].held