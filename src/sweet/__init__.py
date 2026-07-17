from . import _window 

init = _window.GameLoop.init
run = _window.GameLoop.start

Window = _window.Window


__all__ = ["init", "run", "Window"]