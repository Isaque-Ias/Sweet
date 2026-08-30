import sweet
import sweet.plataform.hal as HAL
import sweet.plataform.display as display
from enum import Enum, auto
import glfw

class GraphicsDevice(Enum):
    MODERNGL = auto()

class DisplayModality(Enum):
    MODERNGL = auto()

class Engine:
    @classmethod
    def initialize(cls, graphics_device: GraphicsDevice, display_modality: DisplayModality):
        cls.gfx_device: HAL.manager.GraphicsDevice
        
        if graphics_device == GraphicsDevice.MODERNGL:
            cls.gfx_device = HAL.opengl.mgl.ModernGLGraphicsDevice()
            cls.gfx_device = HAL.opengl.mgl.gfx_device = cls.gfx_device
            cls.gfx_device.initialize()

        if display_modality == DisplayModality.MODERNGL:
            cls._gl_dummy_context()
            cls._window = display.window.moderngl.GLWindow

        sweet.gameplay.skybox.graphics_device = cls.gfx_device
        sweet.gameplay.scene.graphics_device = cls.gfx_device
        sweet.gameplay.assets.Assets.initialize(graphics_device=cls.gfx_device)
        sweet.graphics.upload.UploadManager.initialize(graphics_device=cls.gfx_device)
        sweet.graphics.render.process.PipelineManager.initialize(device=cls.gfx_device) # type: ignore

    @classmethod
    def create_window(cls):
        return cls._window(cls.gfx_device)

    @classmethod
    def _gl_dummy_context(cls):
        if not glfw.init():
            raise RuntimeError("GLFW Falhou")
        
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE) # type: ignore
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4) # type: ignore
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6) # type: ignore
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE) # type: ignore

        dummy_handle = glfw.create_window(1, 1, "[__dummy__]", None, None) # type: ignore
        if not dummy_handle:
            glfw.terminate()
            raise RuntimeError("Janela Dummy de GLFW falhou")

        glfw.make_context_current(dummy_handle) # type: ignore

        display.window.moderngl.GLWindow._PRIMARY_WINDOW_HANDLE = dummy_handle # type: ignore

    # @classmethod
    # def shutdown_engine_graphics(graphics_device, active_windows: list = None) -> None:
    #     glfw.make_context_current(None)

    #     if active_windows:
    #         for win in active_windows:
    #             if hasattr(win, "wnd") and win.wnd:
    #                 # If wrapped in a proxy or raw handle
    #                 raw_handle = getattr(win.wnd, "_window", win.wnd)
    #                 if raw_handle:
    #                     glfw.destroy_window(raw_handle)

    #     # 3. Destroy the primary dummy window context
    #     dummy_handle = getattr(graphics_device, "_dummy_window", None)
    #     if dummy_handle:
    #         glfw.destroy_window(dummy_handle)
    #         graphics_device._dummy_window = None

    #     # 4. Reset global window handles
    #     if hasattr(GLWindow, "_PRIMARY_WINDOW_HANDLE"):
    #         GLWindow._PRIMARY_WINDOW_HANDLE = None

    #     # 5. Release ModernGL Context (if release implementation exists)
    #     if hasattr(graphics_device, "ctx") and graphics_device.ctx:
    #         if hasattr(graphics_device.ctx, "release"):
    #             graphics_device.ctx.release()
    #         graphics_device.ctx = None

    #     # 6. Terminate the GLFW library
    #     glfw.terminate()
    #     print("[Engine] Graphics subsystem successfully shut down.")