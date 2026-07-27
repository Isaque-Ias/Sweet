"""
SWEET
"""

from . import core as core
from . import plataform as plataform
from . import resources as resources
from . import graphics as graphics
from . import gameplay as gameplay
from . import app as app
from .plataform.display.implementation.window import Window as Window# type: ignore
from .gameplay.assets import Assets as Assets# type: ignore
from .core import linalg as linalg

def start() -> None: ...
def stop() -> None: ...
