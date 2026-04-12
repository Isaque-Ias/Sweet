import pygame as pg
from pynput import keyboard
import pyperclip

class Input:
    _mouse_pos: tuple = (0, 0)
    _keys: dict = {121: [False] * 3}
    _input: bool = False
    _focus: bool = False
    _mouse: dict = {pg.BUTTON_LEFT: [False] * 3, pg.BUTTON_RIGHT: [False] * 3, pg.BUTTON_MIDDLE: [False] * 3}
    mouse_scroll_x: int = 0
    mouse_scroll_y: int = 0

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
    def get_mouse_pos(cls) -> tuple:
        return cls._mouse_pos

    @classmethod
    def update(cls) -> None:
        keys = pg.key.get_pressed()
        for inp in cls._keys:
            cls._keys[inp][0] = False
            cls._keys[inp][1] = False
            
            if keys[inp]:
                if not cls._keys[inp][2]:
                    cls._keys[inp][0] = True

                cls._keys[inp][2] = True
            else:
                if cls._keys[inp][2]:
                    cls._keys[inp][1] = True

                cls._keys[inp][2] = False

        cls._mouse_pos = pg.mouse.get_pos()
        buttons = pg.mouse.get_pressed()
        
        for inp in cls._mouse:
            cls._mouse[inp][0] = False
            cls._mouse[inp][1] = False

            if buttons[int(inp) - 1]:
                if not cls._mouse[inp][2]:
                    cls._mouse[inp][0] = True

                cls._mouse[inp][2] = True
            else:
                if cls._mouse[inp][2]:
                    cls._mouse[inp][1] = True

                cls._mouse[inp][2] = False

    @classmethod
    def get_keys(cls) -> dict:
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
    
class InputListener:
    pressed_modifiers = set()

    def __init__(self, ignored_combos=None, feed=[], esc_logic=lambda a: False, enter_logic=lambda a: False, exiting_logic=lambda a: None, shift_operations=True):
        self.ignored_combos = ignored_combos
        self.input_feed = feed
        self.history_scroll = -1
        self.current_chat = ""
        self.message = ""
        self.pointer = 0
        self.select_pointer = 0
        self.shift_operations = shift_operations
        
        self.esc_logic = esc_logic
        self.enter_logic = enter_logic
        self.exiting_logic = exiting_logic

        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
    
    @classmethod
    def get_modifiers(cls):
        mods = []
        if any(m in cls.pressed_modifiers for m in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
            mods.append("ctrl")
        if any(m in cls.pressed_modifiers for m in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)):
            mods.append("shift")
        if any(m in cls.pressed_modifiers for m in (keyboard.Key.alt_l, keyboard.Key.alt_r)):
            mods.append("alt")
        return mods
    
    def insert_text(self, text):
        self.message = self.message[:self.pointer] + text + self.message[self.pointer:]
        self.set_pointer(self.pointer + len(text), False)

    def remove_text(self, pos):
        self.message = self.message[:pos] + self.message[pos + 1:]
        if self.pointer > pos: self.set_pointer(self.pointer - 1, False)
        
    def remove_text_chunk(self, pos, end):
        self.message = self.message[:end] + self.message[pos + 1:]
        if self.pointer > pos: self.set_pointer(self.pointer - (pos - end + 1), False)

    def set_text(self, text):
        self.message = text
        self.set_pointer(len(text), False)

    def set_pointer(self, value, shift):
        if not shift:
            self.select_pointer = value
        self.pointer = value
    
    def get_selection_text(self):
        return self.message[min(self.pointer, self.select_pointer):max(self.pointer, self.select_pointer)]

    def remove_selection(self, is_shift):
        if not self.shift_operations:
            self.select_pointer = self.pointer
        if abs(self.pointer - self.select_pointer) > 0:
            big, small = max(self.pointer, self.select_pointer) - 1, min(self.pointer, self.select_pointer)
            self.remove_text_chunk(big, small)
            self.select_pointer = self.pointer
            return True
        return False

    def on_press(self, key):
        if not Input.get_focus():
           return
        
        mods = self.get_modifiers()
        is_ctrl = "ctrl" in mods
        is_shift = "shift" in mods
        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.left:
                if self.pointer > 0:
                    if is_ctrl:
                        idx = self.message[:self.pointer].rstrip().rfind(" ")
                        if idx == -1:
                            self.set_pointer(0, is_shift)
                            return

                        self.set_pointer(idx + 1, is_shift)
                        return

                    self.set_pointer(self.pointer - 1, is_shift)

            if key == keyboard.Key.right:
                if self.pointer < len(self.message):
                    if is_ctrl:
                        segment = self.message[self.pointer:]
                        skip = 0
                        while skip < len(segment) and segment[skip].isspace():
                            skip += 1
                        idx = segment.find(" ", skip)
                        if idx == -1:
                            self.set_pointer(len(self.message), is_shift)
                        else:
                            self.set_pointer(self.pointer + idx, is_shift)
                        return

                    self.set_pointer(self.pointer + 1, is_shift)
            
            if key == keyboard.Key.up:
                if self.history_scroll == -1:
                    self.current_chat = self.message
                
                if self.history_scroll + 1 >= len(self.input_feed):
                    return
                
                self.history_scroll += 1
                self.set_text(self.input_feed[self.history_scroll])
    
                return
            
            if key == keyboard.Key.down:
                if self.history_scroll == 0:
                    self.set_text(self.current_chat)
                    self.history_scroll = -1
                    return

                if self.history_scroll == -1:
                    return
                
                self.history_scroll -= 1
                self.set_text(self.input_feed[self.history_scroll])
                return

            if key == keyboard.Key.space:
                self.remove_selection(is_shift)

                self.insert_text(" ")
                return

            if key == keyboard.Key.backspace:
                if self.remove_selection(is_shift):
                    return
                if len(self.message[:self.pointer]) > 0:
                    
                    if is_ctrl:
                        idx = self.message[:self.pointer].rstrip().rfind(" ")
                        if idx == -1:
                            self.remove_text_chunk(self.pointer - 1, 0)
                        else:
                            self.remove_text_chunk(self.pointer - 1, idx + 1)
                    else:
                        self.remove_text(self.pointer - 1)

                return

            if key == keyboard.Key.delete:
                if self.remove_selection(is_shift):
                    return
                if self.pointer < len(self.message):
                    
                    if is_ctrl:
                        segment = self.message[self.pointer:]
                        skip = 0
                        while skip < len(segment) and segment[skip].isspace():
                            skip += 1
                        idx = segment.find(" ", skip)
                        if idx == -1:
                            self.remove_text_chunk(len(self.message), self.pointer)
                        else:
                            self.remove_text_chunk(self.pointer + idx - 1, self.pointer)
                        return
                    
                    else:
                        self.remove_text(self.pointer)

                return

            self.pressed_modifiers.add(key)
            return

        char = key.char
        if char is None:
            return
        char = char.lower()
        combo = tuple(mods + [char])

        if combo in self.ignored_combos:
            return
        
        if is_ctrl:
            c = char.lower()

            if self.shift_operations:
                if c == "\x03":
                    selection = self.get_selection_text()
                    if selection:
                        pyperclip.copy(selection)
                    return

                if c == "\x16":
                    data = pyperclip.paste()
                    if isinstance(data, str) and data:
                        self.remove_selection(is_shift)
                        self.insert_text(data)
                    return

                if c == "\x18":
                    selection = self.get_selection_text()
                    if selection:
                        pyperclip.copy(selection)
                        self.remove_selection(is_shift)
                    return

            return

        caps = Input.get_caps()
        caps_case = not caps if is_shift else caps
        added_info = key.char.upper() if caps_case else key.char.lower()
        
        self.remove_selection(is_shift)
        self.insert_text(added_info)

    def on_release(self, key):
        if not Input.get_focus():
            return
        
        if key in self.pressed_modifiers:
            self.pressed_modifiers.remove(key)

        if key == keyboard.Key.esc:
            return self.esc_logic(self.message)
        
        if key == keyboard.Key.enter:
            return self.enter_logic(self.message)
        
        return self.exiting_logic(self.message)