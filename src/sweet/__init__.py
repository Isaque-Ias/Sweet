from . import core, plataform, resources, graphics, gameplay, app # type: ignore

linalg = core.linalg
Window = plataform.display.implementation.window.Window
Assets = gameplay.assets.Assets

if core.system.state.engine.render == "GLCONTEXT":
    gl_context = plataform.renderer.render_device.GLContext.use_context()
    graphics.gl.shaders.ShaderManager.set_context(gl_context)
    graphics.gl.upload.GeometryUploader.set_context(gl_context)
    graphics.gl.upload.TextureUploader.set_context(gl_context)
    graphics.gl.render.ShaderRender.set_context(gl_context)

start = app.loop.start
stop = app.loop.stop