from . import core as core
from . import plataform as plataform
from . import resources as resources
from . import graphics as graphics
from . import gameplay as gameplay
from . import app as app
from .plataform.hal.manager import RenderTarget as RenderTarget
from .plataform.display.window.window import WindowSurface as WindowSurface # type: ignore
from .plataform.inputs.mapping.input_codes import Key as Key
from .gameplay.assets import Assets as Assets # type: ignore
from .gameplay.entity import Entity as Entity
from .gameplay.entity import GameModel as GameModel
from .gameplay.scene import Scene as Scene
from .gameplay.camera import Camera as Camera
from .gameplay.view import View as View
from .gameplay.view import UpdatePolicy as UpdatePolicy
from .gameplay.visual import Visual as Visual
GameModel = gameplay.entity.GameModel
from .core import linalg as linalg

gfx_device: plataform.hal.manager.GraphicsDevice
asset_manager: gameplay.assets.Assets

Engine = app.engine.Engine
GraphicsDevice = app.engine.GraphicsDevice
DisplayModality = app.engine.DisplayModality

Entity = gameplay.entity.Entity
Scene = gameplay.scene.Scene
Visual = gameplay.visual.Visual
Camera = gameplay.camera.Camera
UpdatePolicy = gameplay.view.UpdatePolicy

def start() -> None: ...
def stop() -> None: ...
