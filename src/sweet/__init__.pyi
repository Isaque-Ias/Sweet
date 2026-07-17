def init() -> None: ...
def run() -> None: ...
class Window:
    def __init__(self,
                 title: str = "[Sem Nome]",
                 size: tuple[int, int] = (1280, 720),
                 pos: tuple[int, int] | None = None,
                 fullscreen: bool = False,
                 resizable: bool = False,
                 color: tuple[float, float, float, float] = (0, 0, 0, 1),
                 borderless: bool = False,
                 pixel_samples: int = 4) -> None: ...
    
    def run(self) -> None: ...