from . import core, plataform # type: ignore

from . import resources, graphics, gameplay, app # type: ignore

Engine = app.engine.Engine
GraphicsDevice = app.engine.GraphicsDevice
DisplayModality = app.engine.DisplayModality

linalg = core.linalg
Assets = gameplay.assets.Assets
Entity = gameplay.entity.Entity
Component = gameplay.entity.Component
Scene = gameplay.scene.Scene
Camera = gameplay.camera.Camera
GameModel = gameplay.entity.GameModel
View = gameplay.view.View
Visual = gameplay.visual.Visual
UpdatePolicy = gameplay.view.UpdatePolicy

GLWindow = plataform.display.window.moderngl.GLWindow
Key = plataform.inputs.mapping.input_codes.Key

start = app.loop.start
stop = app.loop.stop
