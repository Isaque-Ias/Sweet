from dataclasses import dataclass
from ..common import ActionState
from ..mapping.input_codes import MouseButton
from ..mapping._keymapper import GenericMapper

@dataclass
class MouseState:
    released: bool = False
    pressed: bool = False
    held: bool = False

class MouseInput:
    def __init__(self) -> None:
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_delta: tuple[int, int] = (0, 0)
        
        self._mouse: dict[MouseButton, MouseState] = {}

        self.mouse_scroll_x: float = 0
        self.mouse_scroll_y: float = 0

    def process_mouse_event(self, generic_button: int, action: ActionState, mapper: GenericMapper):
        button = mapper.to_sweet_mouse(generic_button)

        if button not in self._mouse:
            self._mouse[button] = MouseState()

        self._mouse[button].pressed = False
        self._mouse[button].released = False

        if action == ActionState.PRESS:
            if not self._mouse[button].held:
                self._mouse[button].pressed = True
            self._mouse[button].held = True

        elif action == ActionState.RELEASE:
            if self._mouse[button].held:
                self._mouse[button].released = True
            self._mouse[button].held = False

    def update_mouse_pos(self, x: int, y: int):
        self._mouse_pos = (x, y)

    def update_mouse_delta(self, dx: int, dy: int) -> None:
        self._mouse_delta = (dx, dy)

    def get_mouse_delta(self) -> tuple[int, int]:
        return self._mouse_delta

    def get_mouse_pos(self) -> tuple[int, int]:
        return self._mouse_pos

    def is_mouse_pressed(self, button: MouseButton) -> bool:
        return self._mouse[button].pressed

    def is_mouse_released(self, button: MouseButton) -> bool:
        return self._mouse[button].released

    def is_mouse_held(self, button: MouseButton) -> bool:
        return self._mouse[button].held
