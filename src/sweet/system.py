from colorama import init, Fore
from typing import Any
from pathlib import Path
import json
from pathlib import Path

init(autoreset=True)

class ConfigObject:
    def __init__(self, data: dict[str, Any], fallback_data: dict[str, Any] | None = None):
        super().__setattr__("_data", data)
        super().__setattr__("_fallback_data", fallback_data or {})
        
    def __getattr__(self, key: str) -> Any:
        self._fallback_data: dict[str, Any] | None

        if key in self._data:
            value = self._data[key]
            if isinstance(value, dict):
                next_fallback = self._fallback_data.get(key) if isinstance(self._fallback_data, dict) else None
                return ConfigObject(value, fallback_data=next_fallback)
            return value

        if isinstance(self._fallback_data, dict):
            if key in self._fallback_data:
                fallback_value = self._fallback_data[key]
                if isinstance(fallback_value, dict):
                    return ConfigObject({}, fallback_data=fallback_value)
                return fallback_value

        return None

    def __repr__(self) -> str:
        return f"ConfigObject(data={self._data}, fallback={self._fallback_data})"

class SysMeta(type):
    _config_path: Path | str = Path()
    _config_map: ConfigObject | None = None
    _fallback_raw_data: dict[str, Any] = {}

    def __init__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]):
        super().__init__(name, bases, attrs)
        cls._fallback_raw_data = cls.load_fallback_data()
        cls._config_path = Path(__file__).parent / "build" / "__config__.json"
        cls._config_map = None

    @staticmethod
    def success(message: Any):
        print(f"{Fore.GREEN}{message}")

    @staticmethod
    def warn(message: Any):
        print(f"{Fore.YELLOW}{message}")

    @staticmethod
    def problem(message: Any):
        print(f"{Fore.RED}{message}")

    @staticmethod
    def solve_path(path: str | Path) -> Path:
        if isinstance(path, Path):
            return path
        
        norm_path = Path(path.replace("\\", "/"))
        absolute_path = Path.cwd() / norm_path

        return absolute_path

    @classmethod
    def load_fallback_data(cls) -> dict[str, Any]:
        BASE = Path(__file__).parent
        PATH = BASE / "build" / "__config__.json"
        with open(PATH, "r") as file:
            return json.load(file)

    @property
    def config(cls) -> ConfigObject:
        if cls._config_map is None:
            
            cls._config_map = cls._load_config(cls._config_path, cls._fallback_raw_data)
        return cls._config_map

    @config.setter
    def config(cls, value: Path | str):
        cls._config_path = value
        
        cls._config_map = cls._load_config(value, cls._fallback_raw_data)
    
    @classmethod
    def _load_config(cls, path: Path | str, fallback: dict[str, Any]) -> ConfigObject:
        solved_path = cls.solve_path(path)
        
        if not solved_path.exists():
            config_json = cls.load_fallback_data()
            System.warn(f"Arquivo de configuração em: {path} não encontrado. Utilizando configuração padrão.")
        else:
            with open(solved_path, "r") as file:
                config_json = json.load(file)

        return ConfigObject(config_json, fallback_data=fallback)

class System(metaclass=SysMeta):
    pass