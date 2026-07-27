from colorama import init, Fore
from typing import Any, cast
from pathlib import Path
import json
from dataclasses import dataclass
from datetime import datetime
import os
import sys
import traceback
from typing import Union, Optional

# Built in

@staticmethod
def solve_path(path: str | Path) -> Path:
    if isinstance(path, Path):
        return path
    
    norm_path = Path(path.replace("\\", "/"))
    absolute_path = Path.cwd() / norm_path

    return absolute_path

def _init_helper(path: Path):
    if not path.exists():
        raise FileNotFoundError("Erro durante inicialização. Por favor reinstale o módulo")
    else:
        with open(path, "r") as file:
            return json.load(file)

_BASE = Path(__file__).parent
_ENV = _BASE / "env.json"
_ENGINE = _BASE / "engine.json"
_BUILTIN_ENV: dict[str, Any] = _init_helper(_ENV)
_BUILTIN_ENGINE: dict[str, Any] = _init_helper(_ENGINE)

# loading

class ConfigObject:
    def __init__(self, data: dict[str, Any], fallback: dict[str, Any] | None = None):
        fallback = fallback or {}
        self._fallback: dict[str, Any] | None
        self.__dict__["_fallback"] = fallback or {}
        
        for key, value in data.items():
            fb_value = self._fallback.get(key) if isinstance(self._fallback, dict) else None
            if isinstance(value, dict):
                self.__dict__[key] = ConfigObject(value, fb_value)
            else:
                self.__dict__[key] = value

    def __getattr__(self, item: str) -> Any:
        if item not in self.__dict__:
            fb_val = self._fallback.get(item) if isinstance(self._fallback, dict) else None
            if fb_val is not None:
                if isinstance(fb_val, dict):
                    return ConfigObject({}, fb_val)
                return fb_val
            raise AttributeError(f"Configuração '{item}' não encontrada")
        return self.__dict__[item]

    def __setattr__(self, key: str, value: Any):
        if value is None:
            fb_val = self._fallback.get(key) if isinstance(self._fallback, dict) else None
            if fb_val is not None:
                if isinstance(fb_val, dict):
                    self.__dict__[key] = ConfigObject({}, fb_val)
                else:
                    self.__dict__[key] = fb_val
                return
            
        if isinstance(value, dict):
            fb_val = self._fallback.get(key) if isinstance(self._fallback, dict) else None
            self.__dict__[key] = ConfigObject(value, fb_val)
        else:
            self.__dict__[key] = value

    def load_from_dict(self, data: dict[str, Any]):
        for key, value in data.items():
            fb_value = self._fallback.get(key) if isinstance(self._fallback, dict) else None
            if isinstance(value, dict):
                if key in self.__dict__ and isinstance(self.__dict__[key], ConfigObject):
                    self.__dict__[key].load_from_dict(value)
                else:
                    self.__dict__[key] = ConfigObject(value, fb_value)
            else:
                self.__dict__[key] = value

    def __repr__(self):
        display_dict = {k: v for k, v in self.__dict__.items() if k != "_fallback"}
        return str(display_dict)

class State:
    def __init__(self):
        self._env = ConfigObject(_BUILTIN_ENV, fallback=_BUILTIN_ENV)
        self._engine = ConfigObject(_BUILTIN_ENGINE, fallback=_BUILTIN_ENGINE)

    def _load_helper(self, path: str, default_config: dict[str, Any]):
        solved_path = solve_path(path)

        if not solved_path.exists():
            external_data = default_config
            warn(f"Arquivo de configuração em: {path} não encontrado. Utilizando configuração padrão.", force=True)
        else:
            with open(solved_path, "r") as file:
                external_data = cast(dict[str, Any], json.load(file))

        return external_data

    @property
    def env(self) -> ConfigObject:
        return self._env

    @env.setter
    def env(self, value: dict[str, Any]):
        self._env.load_from_dict(value)

    @property
    def engine(self) -> ConfigObject:
        return self._engine

    @engine.setter
    def engine(self, value: dict[str, Any]):
        self._engine.load_from_dict(value)

state = State()

# config object

init(autoreset=True)

def success(*message: Any, sep: str=" "):
    final_text = ""
    for i in range(len(message)):
        final_text = final_text + message[i] + (sep if i + 1 < len(message) else "")
    
    print(f"[Sweet: Success] {Fore.GREEN}{final_text}")

def warn(*message: Any, sep: str=" ", force: bool=False):
    final_text = ""
    for i in range(len(message)):
        final_text = final_text + message[i] + (sep if i + 1 < len(message) else "")

    report_config = state.env.report
    if report_config or force:
        print(f"[Sweet: Warning] {Fore.YELLOW}{final_text}")

def problem(*message: Any, sep: str=" "):
    final_text = ""
    for i in range(len(message)):
        final_text = final_text + message[i] + (sep if i + 1 < len(message) else "")

    print(f"[Sweet: Problem] {Fore.RED}{final_text}")

@dataclass
class Component:
    text: str
    size: int = 3
    color: str = "gray"
    indent: int = 0

    def to_markdown(self) -> str:
        indent_str = "    " * self.indent
        
        if 1 <= self.size <= 6:
            content = f"{'#' * self.size} {self.text}"
        else:
            content = self.text
            
        if self.color:
            content = f'<span style="color: {self.color};">{content}</span>'
            
        return f"{indent_str}{content}"

def crash_relatory(exception: Exception, *comp: Union[str, Component], output: Optional[Path | str]=None):
    error_message = str(exception)
    full_trace = traceback.format_exc()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines = [
        f"# FALHA DE EXECUÇÃO — {timestamp}",
        f"**Tipo de exceção:** `{type(exception).__name__}`",
        f"**Mensagem de erro:** {error_message}",
        "\n## Contexto",
    ]
    
    for item in comp:
        if isinstance(item, str):
            normalized = Component(text=item, size=0, color="", indent=0)
        else:
            normalized = item
            
        report_lines.append(normalized.to_markdown())
        
    report_lines.extend([
        "\n## Traceback:",
        "```python",
        full_trace.strip(),
        "```"
    ])
    
    full_report = "\n".join(report_lines)

    print(state.env)

    if state.env.crash_report:
        if output:
            filepath = solve_path(output)
        else:
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        
            crash_dir = os.path.join(app_dir, "crashes")
            os.makedirs(crash_dir, exist_ok=True)
            
            filename = datetime.now().strftime("crash_%Y%m%d_%H%M%S.md")
            filepath = os.path.join(crash_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(full_report)
            print(f"[Sweet: Crash] {Fore.BLUE}Report safely archived to: {filepath}")
        except IOError as e:
            print(f"[Sweet: Crash] {Fore.RED}Failed to write crash dump file: {e}", file=sys.stderr)
            
    return full_report