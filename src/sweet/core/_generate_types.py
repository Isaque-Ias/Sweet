import json
from pathlib import Path
from typing import Any

def json_to_pyi_classes(config_preffix: str, data: dict[str, Any], current_path: list[str] | None = None) -> list[str]:
    if current_path is None:
        current_path = []

    lines: list[str] = []
    nested_classes: list[str] = []
    fields: list[str] = []

    for key, value in data.items():
        if isinstance(value, dict):
            path_hierarchy = current_path + [key]
            sub_class_name = config_preffix + "_" + "_".join(k.title().replace('_', '') for k in path_hierarchy)
            
            fields.append(f"    {key}: {sub_class_name}")
            nested_classes.extend(json_to_pyi_classes(config_preffix, value, path_hierarchy))
        else:
            type_name = type(value).__name__
            if type_name == "NoneType":
                type_name = "Any"
            fields.append(f"    {key}: {type_name}")

    lines.extend(nested_classes)
    
    if not current_path:
        class_name = config_preffix + "Config"
    else:
        class_name = config_preffix + "_" + "_".join(k.title().replace('_', '') for k in current_path)

    lines.append(f"class {class_name}:")
    if not fields:
        lines.append("    ... ")
    else:
        lines.extend(fields)
        lines.append("    def load_from_dict(self, data: dict[str, Any]) -> None: ...")
    lines.append("")
    return lines

def _load_helper(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo raiz não foi encontrado em: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data

def generate_stub_file():
    base_dir = Path(__file__).parent
    env_path = base_dir / "env.json"
    engine_path = base_dir / "engine.json"
    pyi_path = base_dir / "system.pyi"

    env_data = _load_helper(env_path)
    engine_data = _load_helper(engine_path)

    stub_content = [
        "# Código gerado automaticamente. Não edite.",
        "",
        "from typing import Any",
        "from pathlib import Path",
        ""
    ]
    
    stub_content.extend(json_to_pyi_classes("Env", env_data))

    stub_content.extend(json_to_pyi_classes("Engine", engine_data))
    
    def add_stub(*lines: str):
        for line in lines:
            stub_content.append(line)
        stub_content.append("")
    
    add_stub(
        "class State:",
        "   @property",
        "   def engine(self) -> EngineConfig: ...",
        "",
        "   @property",
        "   def env(self) -> EnvConfig: ...",
        "",
        "   @engine.setter",
        "   def engine(self, value: dict[str, Any]) -> None: ...",
        "",
        "   @env.setter",
        "   def env(self, value: dict[str, Any]) -> None: ...",
        "",
        "state: State",
             )

    add_stub(
        "from pathlib import Path",
        "from typing import Union, Optional",
        "from dataclasses import dataclass",
    )

    add_stub(
        "@dataclass",
        "class Component:",
        "   text: str",
        "   size: int = 3",
        "   color: str = 'gray'",
        "   indent: int = 0",
        "   def to_markdown(self) -> str: ..."
        )
    add_stub("def warn(message: str, force: bool = False) -> None: ...")
    add_stub("def problem(message: str) -> None: ...")
    add_stub("def success(message: str) -> None: ...")
    add_stub("def crash_relatory(exception: Exception, *comp: Union[str, Component], output: Optional[Path | str] = None) -> list[str]: ...")
    add_stub("def load_env_config(path: str | Path) -> None: ...")
    add_stub("def load_engine_config(path: str | Path) -> None: ...")
    add_stub("def solve_path(path: str | Path) -> Path: ...")

    with open(pyi_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stub_content))
    
    (f"Sucesso! arquivo criado: {pyi_path}")

if __name__ == "__main__":
    generate_stub_file()
