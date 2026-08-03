from moderngl_window.timers.clock import Timer
import glfw
from sweet.gameplay.views.view import ViewManager
from sweet.plataform.display.manager import DisplayManager
from sweet.graphics.pipeline.manager import PipelineManager
from sweet.gameplay.scene import SceneManager
from sweet.gameplay.entity import Entity
from sweet.plataform.hal.manager import GraphicsDeviceManager
from sweet.core.system import state

ticks_per_second: int = 60

_running = False
_time_accumulator = 0.0
_tick_delta = 1.0 / ticks_per_second

def start():
    global timer, _running, _gfx_device

    _gfx_device = GraphicsDeviceManager.query_devices(state.engine.HAL)
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
    global _running, _time_accumulator, _tick_delta, _gfx_device
    displays = DisplayManager.query_displays()
    if not displays:
        stop()
        return

    _, delta_time = timer.next_frame()

    delta_time = min(delta_time, 0.25)

    _time_accumulator += delta_time

    while _time_accumulator >= _tick_delta:
        _update(_tick_delta)
        
        tick_views = ViewManager.get_tick_views()
        for view in tick_views:
            view.tick()
            
        _time_accumulator -= _tick_delta
    
    active_windows_count = 0

    for display in displays:
        poll = display.poll_events()
        if not poll:
            display.close()
            continue
        active_windows_count += 1

    if active_windows_count == 0:
        _running = False

    alpha = _time_accumulator / _tick_delta
    render(alpha)

def _entity_logic(entities: list[Entity]):
    for entity in entities:
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
        _, win = view.get_target()
        
        if win and hasattr(win, 'is_active') and not win.is_active():
            continue

        PipelineManager.process(view)
        view.clear_demand()

def _cleanup():
    for display in DisplayManager.query_displays():
        display.close()

    _gfx_device.shutdown()

    glfw.terminate()

def stop():
    global _running
    _running = False