from pathlib import Path

def solve_path(path: str | Path) -> Path:
    if isinstance(path, Path):
        return path
    
    norm_path = Path(path.replace("\\", "/"))

    absolute_path = Path.cwd() / norm_path

    return absolute_path