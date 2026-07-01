from moderngl_window.context.base import BaseWindow
from moderngl_window.context.base.keys import BaseKeys
import glfw
class Input:
    _mouse_pos: tuple[int, int] = (0, 0)
    _keys: dict[int, list[bool]] = {121: [False] * 3}
    _input: bool = False
    _focus: bool = False
    _mouse: dict[int, list[bool]] = {1: [False] * 3, 2: [False] * 3, 3: [False] * 3}
    mouse_scroll_x: float = 0
    mouse_scroll_y: float = 0
    _caps: bool = False
    wnd: BaseWindow
    key_code: BaseKeys

    @classmethod
    def set_caps(cls, value: bool) -> None:
        cls._caps = value

    @classmethod
    def get_caps(cls) -> bool:
        return cls._caps

    @classmethod
    def set_focus(cls, value: bool) -> None:
        cls._focus = value

    @classmethod
    def get_focus(cls) -> bool:
        return cls._focus

    @classmethod
    def set_mouse_pos(cls, x: int, y: int) -> None:
        glfw.set_cursor_pos(cls.wnd._window, x, y)  # type: ignore
        cls._mouse_pos = (x, y)

    @classmethod
    def get_mouse_pos(cls) -> tuple[int, int]:
        return cls._mouse_pos

    @classmethod
    def set_mouse_visibility(cls, visible: bool) -> None:
        cls.wnd.cursor = visible

    @classmethod
    def process_key_event(cls, key: int, action: int, keys_enum: BaseKeys):
        if key not in cls._keys:
            cls._keys[key] = [False, False, False]

        cls._keys[key][0] = False
        cls._keys[key][1] = False

        if action == keys_enum.ACTION_PRESS:
            if not cls._keys[key][2]:
                cls._keys[key][0] = True
            cls._keys[key][2] = True

        elif action == keys_enum.ACTION_RELEASE:
            if cls._keys[key][2]:
                cls._keys[key][1] = True
            cls._keys[key][2] = False

    @classmethod
    def process_mouse_button_event(cls, button: int, action: int, keys_enum: BaseKeys):
        button_str = button + 1

        if button_str not in cls._mouse:
            cls._mouse[button_str] = [False, False, False]

        cls._mouse[button_str][0] = False
        cls._mouse[button_str][1] = False

        if action == keys_enum.ACTION_PRESS:
            if not cls._mouse[button_str][2]:
                cls._mouse[button_str][0] = True
            cls._mouse[button_str][2] = True

        elif action == keys_enum.ACTION_RELEASE:
            if cls._mouse[button_str][2]:
                cls._mouse[button_str][1] = True
            cls._mouse[button_str][2] = False

    @classmethod
    def clear_frame_deltas(cls):
        for key in cls._keys:
            cls._keys[key][0] = False
            cls._keys[key][1] = False
        for btn in cls._mouse:
            cls._mouse[btn][0] = False
            cls._mouse[btn][1] = False

    @classmethod
    def get_keys(cls):
        return cls._keys

    @classmethod
    def get_pressed(cls, key: int) -> bool:
        if cls._keys.get(key) == None:
            cls._keys[key] = [False] * 3

        return cls._keys[key][0]

    @classmethod
    def get_released(cls, key: int) -> bool:
        if cls._keys.get(key) == None:
            cls._keys[key] = [False] * 3

        return cls._keys[key][1]

    @classmethod
    def get_press(cls, key: int) -> bool:
        if cls._keys.get(key) == None:
            cls._keys[key] = [False] * 3

        return cls._keys[key][2]

    @classmethod
    def mouse_pressed(cls, key: int) -> bool:
        return cls._mouse[key][0]

    @classmethod
    def mouse_released(cls, key: int) -> bool:
        return cls._mouse[key][1]

    @classmethod
    def mouse_press(cls, key: int) -> bool:
        return cls._mouse[key][2]
    
# class InputListener:
#     pressed_modifiers: set[keyboard.Key] = set()

#     def __init__(
#         self,
#         ignored_combos: list[tuple[str, str]] = [],
#         feed: list[str] = [],
#         esc_logic: Callable[..., None] = lambda: None,
#         enter_logic: Callable[..., None] = lambda: None,
#         exiting_logic: Callable[..., None] = lambda: None,
#         shift_operations: bool = True,
#     ):
#         self.ignored_combos = ignored_combos
#         self.input_feed: list[str] = feed
#         self.history_scroll: int = -1
#         self.current_chat: str = ""
#         self.message: str = ""
#         self.pointer: int = 0
#         self.select_pointer: int = 0
#         self.shift_operations: bool = shift_operations

#         self.esc_logic = esc_logic
#         self.enter_logic = enter_logic
#         self.exiting_logic = exiting_logic

#         self.listener = keyboard.Listener(
#             on_press=self.on_press, on_release=self.on_release
#         )
#         self.listener.start()

#     @classmethod
#     def get_modifiers(cls):
#         mods: list[str] = []
#         if any(
#             m in cls.pressed_modifiers
#             for m in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
#         ):
#             mods.append("ctrl")
#         if any(
#             m in cls.pressed_modifiers
#             for m in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
#         ):
#             mods.append("shift")
#         if any(
#             m in cls.pressed_modifiers for m in (keyboard.Key.alt_l, keyboard.Key.alt_r)
#         ):
#             mods.append("alt")
#         return mods

#     def insert_text(self, text: str):
#         self.message = (
#             self.message[: self.pointer] + text + self.message[self.pointer :]
#         )
#         self.set_pointer(self.pointer + len(text), False)

#     def remove_text(self, pos: int):
#         self.message = self.message[:pos] + self.message[pos + 1 :]
#         if self.pointer > pos:
#             self.set_pointer(self.pointer - 1, False)

#     def remove_text_chunk(self, pos: int, end: int):
#         self.message = self.message[:end] + self.message[pos + 1 :]
#         if self.pointer > pos:
#             self.set_pointer(self.pointer - (pos - end + 1), False)

#     def set_text(self, text: str):
#         self.message = text
#         self.set_pointer(len(text), False)

#     def set_pointer(self, value: int, shift: bool):
#         if not shift:
#             self.select_pointer = value
#         self.pointer = value

#     def get_selection_text(self):
#         return self.message[
#             min(self.pointer, self.select_pointer) : max(
#                 self.pointer, self.select_pointer
#             )
#         ]

#     def remove_selection(self):
#         if not self.shift_operations:
#             self.select_pointer = self.pointer
#         if abs(self.pointer - self.select_pointer) > 0:
#             big, small = max(self.pointer, self.select_pointer) - 1, min(
#                 self.pointer, self.select_pointer
#             )
#             self.remove_text_chunk(big, small)
#             self.select_pointer = self.pointer
#             return True
#         return False

#     def on_press(self, key: keyboard.Key | keyboard.KeyCode | None):
#         if key == None:
#             return

#         if not Input.get_focus():
#             return

#         mods = self.get_modifiers()
#         is_ctrl = "ctrl" in mods
#         is_shift = "shift" in mods
#         if isinstance(key, keyboard.Key):
#             if key == keyboard.Key.left:
#                 if self.pointer > 0:
#                     if is_ctrl:
#                         idx = self.message[: self.pointer].rstrip().rfind(" ")
#                         if idx == -1:
#                             self.set_pointer(0, is_shift)
#                             return

#                         self.set_pointer(idx + 1, is_shift)
#                         return

#                     self.set_pointer(self.pointer - 1, is_shift)

#             if key == keyboard.Key.right:
#                 if self.pointer < len(self.message):
#                     if is_ctrl:
#                         segment = self.message[self.pointer :]
#                         skip = 0
#                         while skip < len(segment) and segment[skip].isspace():
#                             skip += 1
#                         idx = segment.find(" ", skip)
#                         if idx == -1:
#                             self.set_pointer(len(self.message), is_shift)
#                         else:
#                             self.set_pointer(self.pointer + idx, is_shift)
#                         return

#                     self.set_pointer(self.pointer + 1, is_shift)

#             if key == keyboard.Key.up:
#                 if self.history_scroll == -1:
#                     self.current_chat = self.message

#                 if self.history_scroll + 1 >= len(self.input_feed):
#                     return

#                 self.history_scroll += 1
#                 self.set_text(self.input_feed[self.history_scroll])

#                 return

#             if key == keyboard.Key.down:
#                 if self.history_scroll == 0:
#                     self.set_text(self.current_chat)
#                     self.history_scroll = -1
#                     return

#                 if self.history_scroll == -1:
#                     return

#                 self.history_scroll -= 1
#                 self.set_text(self.input_feed[self.history_scroll])
#                 return

#             if key == keyboard.Key.space:
#                 self.remove_selection()

#                 self.insert_text(" ")
#                 return

#             if key == keyboard.Key.backspace:
#                 if self.remove_selection():
#                     return
#                 if len(self.message[: self.pointer]) > 0:

#                     if is_ctrl:
#                         idx = self.message[: self.pointer].rstrip().rfind(" ")
#                         if idx == -1:
#                             self.remove_text_chunk(self.pointer - 1, 0)
#                         else:
#                             self.remove_text_chunk(self.pointer - 1, idx + 1)
#                     else:
#                         self.remove_text(self.pointer - 1)

#                 return

#             if key == keyboard.Key.delete:
#                 if self.remove_selection():
#                     return
#                 if self.pointer < len(self.message):

#                     if is_ctrl:
#                         segment = self.message[self.pointer :]
#                         skip = 0
#                         while skip < len(segment) and segment[skip].isspace():
#                             skip += 1
#                         idx = segment.find(" ", skip)
#                         if idx == -1:
#                             self.remove_text_chunk(len(self.message), self.pointer)
#                         else:
#                             self.remove_text_chunk(self.pointer + idx - 1, self.pointer)
#                         return

#                     else:
#                         self.remove_text(self.pointer)

#                 return

#             self.pressed_modifiers.add(key)
#             return

#         char = key.char
#         if char is None:
#             return

#         char = char.lower()
#         combo = tuple(mods + [char])

#         if combo in self.ignored_combos:
#             return

#         if is_ctrl:
#             c = char.lower()

#             if self.shift_operations:
#                 if c == "\x03":
#                     selection = self.get_selection_text()
#                     if selection:
#                         pyperclip.copy(selection)
#                     return

#                 if c == "\x16":
#                     data = pyperclip.paste()
#                     if data:
#                         self.remove_selection()
#                         self.insert_text(data)
#                     return

#                 if c == "\x18":
#                     selection = self.get_selection_text()
#                     if selection:
#                         pyperclip.copy(selection)
#                         self.remove_selection()
#                     return

#             return

#         caps = Input.get_caps()
#         caps_case = not caps if is_shift else caps

#         if isinstance(key.char, str):
#             added_info = key.char.upper() if caps_case else key.char.lower()

#             self.remove_selection()
#             self.insert_text(added_info)

#     def on_release(self, key: keyboard.Key | keyboard.KeyCode | None):
#         if not Input.get_focus():
#             return

#         if key in self.pressed_modifiers:
#             self.pressed_modifiers.remove(key)

#         if key == keyboard.Key.esc:
#             return self.esc_logic(self.message)

#         if key == keyboard.Key.enter:
#             return self.enter_logic(self.message)

#         return self.exiting_logic(self.message)
