from . import core, plataform # type: ignore

if core.system.state.engine.HAL == "MODERNGL":
    gfx_device = plataform.hal.opengl.mgl.ModernGLGraphicsDevice()
    gfx_device.initialize()

from . import resources, graphics, gameplay, app # type: ignore

linalg = core.linalg
Assets = gameplay.assets.Assets
Entity = gameplay.entity.Entity
Scene = gameplay.scene.Scene
GameModel = gameplay.entity.GameModel
View = gameplay.views.view.View

GLWindow = plataform.display.window.glfw.GLWindow
Key = plataform.inputs.mapping.input_codes.Key

asset_manager = gameplay.assets.Assets(graphics_device=gfx_device) # type: ignore
graphics.pipeline.manager.PipelineManager.set_graphics_device(gfx_device) # type: ignore

start = app.loop.start
stop = app.loop.stop
