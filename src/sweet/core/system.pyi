# Código gerado automaticamente. Não edite.

from typing import Any
from pathlib import Path

class Env_Resources_Importing:
    replace_old_assets: str
    fallback_texture: str
    fallback_model: str
    def load_from_dict(self, data: dict[str, Any]) -> None: ...

class Env_Resources:
    importing: Env_Resources_Importing
    def load_from_dict(self, data: dict[str, Any]) -> None: ...

class EnvConfig:
    report: bool
    crash_report: bool
    resources: Env_Resources
    def load_from_dict(self, data: dict[str, Any]) -> None: ...

class EngineConfig:
    HAL: str
    DISPLAY: str
    def load_from_dict(self, data: dict[str, Any]) -> None: ...

class State:
   @property
   def engine(self) -> EngineConfig: ...

   @property
   def env(self) -> EnvConfig: ...

   @engine.setter
   def engine(self, value: dict[str, Any]) -> None: ...

   @env.setter
   def env(self, value: dict[str, Any]) -> None: ...

state: State

from pathlib import Path
from typing import Union, Optional
from dataclasses import dataclass

@dataclass
class Component:
   text: str
   size: int = 3
   color: str = 'gray'
   indent: int = 0
   def to_markdown(self) -> str: ...

def warn(message: str, force: bool = False) -> None: ...

def problem(message: str) -> None: ...

def success(message: str) -> None: ...

def crash_relatory(exception: Exception, *comp: Union[str, Component], output: Optional[Path | str] = None) -> list[str]: ...

def load_env_config(path: str | Path) -> None: ...

def load_engine_config(path: str | Path) -> None: ...

def solve_path(path: str | Path) -> Path: ...
