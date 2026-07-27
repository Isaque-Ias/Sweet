from moderngl_window.timers.clock import Timer
import glfw
from sweet.gameplay.views.view import ViewManager
from sweet.plataform.display.manager import DisplayManager
from sweet.graphics.gl.render import ShaderRender
from sweet.plataform.display.implementation.window import Window
from sweet.gameplay.scene import SceneManager
from sweet.gameplay.entity import Entity

ticks_per_second: int = 60

_running = False
_time_accumulator = 0.0
_tick_delta = 1.0 / ticks_per_second

def start():
    global timer, _running
    timer = Timer()
    timer.start()
    _running = True

    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")
        
    try:
        while _running:
            _loop()
    finally:
        _cleanup()

def _loop():
    global _running, _time_accumulator, _tick_delta
    displays = DisplayManager.get_active_displays()
    if not displays:
        stop()
        return

    _, delta_time = timer.next_frame()

    _time_accumulator += delta_time

    while _time_accumulator >= _tick_delta:
        _update(_tick_delta)

        for view in ViewManager.get_tick_views():
            view.tick()
            
        _time_accumulator -= _tick_delta

    glfw.poll_events()
    
    for display in displays:
        if isinstance(display, Window) and display.wnd:
            if display.wnd.is_closing:
                display.close()

    alpha = _time_accumulator / _tick_delta
    render(alpha)

def _entity_logic(entity: Entity):
        script = entity.get_script()
        if script:
            script()

        # physics...

def _update(dt: float):
    # delta_time = dt
    active_scenes = SceneManager.get_active_scenes()
    for scene in active_scenes:
        scene.apply_logic(_entity_logic)

def render(alpha: float):
    active_views = ViewManager.get_current_views()
    for view in active_views:
        ShaderRender.render(alpha, view.view, view.projection)

def _cleanup():
    for display in DisplayManager.get_active_displays():
        if isinstance(display, Window):
            display.close()
        
    glfw.terminate()

def stop():
    global _running
    _running = False