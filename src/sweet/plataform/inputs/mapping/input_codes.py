from enum import Enum, auto

class Key(Enum):
    UNDEFINED = auto()
    A = auto()
    B = auto()
    C = auto()
    SPACE = auto()
    ESCAPE = auto()
    CAPS_LOCK = auto()

class MouseButton(Enum):
    UNDEFINED = auto()
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()

class GamepadButton(Enum):
    UNDEFINED = auto()
    A = auto()
    B = auto()
    X = auto()
    Y = auto()
