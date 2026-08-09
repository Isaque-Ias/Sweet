from __future__ import annotations
import glm
from enum import Enum, auto
from sweet.plataform.display.manager import DisplaySurface
from ..core import system
from typing import Any, Optional, TYPE_CHECKING
from ..plataform.hal.manager import RenderTarget
if TYPE_CHECKING:
    from .scene import Scene

class UpdatePolicy(Enum):
    EVERY_FRAME = auto()
    EVERY_N_TICKS = auto()
    ON_DEMAND = auto()
    ONCE = auto()

class View:
    def __init__(self, update_policy: UpdatePolicy = UpdatePolicy.ON_DEMAND, **kwargs: Any) -> None:
        self._total_ticks: int = kwargs.get("tick", 0)
        self._update_policy = update_policy
        self._demanding: bool = False
        self._view: Optional[glm.mat4] = None
        self._projection: Optional[glm.mat4] = None
        self._surface: Optional[DisplaySurface] = None

        self._active: bool = False
        self._target: Optional[RenderTarget] = None
        self._scene: Optional[Scene] = None
        self._viewport: Optional[tuple[int, int, int, int]] = None
        self._updated: bool = False
    
        self._tick: int = 0

        ViewManager.add_view(self)

    def get_viewport(self):
        return self._viewport

    def set_viewport(self, value: tuple[int, int, int, int]):
        self._viewport = value

    def get_target(self) -> tuple[Optional[RenderTarget], Optional[DisplaySurface]]:
        return self._target, self._surface

    def get_scene(self):
        return self._scene

    def set_target(self, target: RenderTarget | DisplaySurface):
        if isinstance(target, DisplaySurface):
            self._surface = target
            self._target = target.render_target
        else:
            self._target = target

    def set_scene(self, scene: Scene):
        self._scene = scene

    @property
    def projection(self):
        return self._projection

    @projection.setter
    def projection(self, projection: glm.mat4x4):
        self._projection = projection

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, view: glm.mat4x4):
        self._view = view

    def get_update_policy(self):
        return self._update_policy
    
    def set_update_policy(self, policy: UpdatePolicy, **kwargs: Any):
        self._update_policy: UpdatePolicy = policy
        if policy == UpdatePolicy.ONCE:
            self._updated = False
            self.add_demand()
            self._updated = True

        elif policy == UpdatePolicy.EVERY_N_TICKS:
            tick = kwargs.get("tick", 0)
            if tick is None or tick <= 0:
                tick = 1

            self._total_ticks = tick
            self._tick = 0

    def tick(self):
        if self._total_ticks <= 0:
            return
        
        if self._demanding: return
        
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._demanding = ViewManager.add_demand(self)
            self._tick = 0

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def is_active(self):
        return self._active

    def should_update(self):
        if self._update_policy == UpdatePolicy.EVERY_FRAME:
            return True
        return self._demanding

    def add_demand(self):
        if not self._active:
            system.problem("Não há como realizar uma demanda em uma visão inativa")
            return

        if not self._update_policy == UpdatePolicy.ON_DEMAND:

            if self._update_policy == UpdatePolicy.ONCE and self._updated:
                system.problem("Atualização única só deve ser chamada após inicialização")
                return
            else:
                system.problem("Demandas de visão são permitidas apenas em políticas de atualização em demanda")
                return

        self._demanding = ViewManager.add_demand(self)

    def clear_demand(self):
        if self._update_policy == UpdatePolicy.EVERY_FRAME:
            return
        ViewManager.clear_demand(self)
        self._demanding = False

class ViewManager:
    _views: list["View"] = []
    _demands: list["View"] = []

    @classmethod
    def add_demand(cls, view: View) -> bool:
        if view in cls._demands:
            system.warn("Demanda de visão chamada antes da conclusão de chamada anterior")
            return False
        cls._demands.append(view)
        return True

    @classmethod
    def clear_demand(cls, view: View) -> bool:
        try:
            cls._demands.remove(view)
            return True
        except ValueError:
            system.warn("Demanda já foi removida")
            return True
        
    @classmethod
    def add_view(cls, view: View) -> None:
        if view in cls._views:
            system.warn("Visão já está sendo gerenciada")
            return

        cls._views.append(view)

    @classmethod
    def get_tick_views(cls) -> list["View"]:
        views: list["View"] = []
        for view in cls._views:
            if view.get_update_policy() == UpdatePolicy.EVERY_N_TICKS and view.is_active():
                views.append(view)

        return views

    @classmethod
    def get_current_views(cls) -> list["View"]:
        views: list["View"] = []
        for view in cls._views:
            if view.is_active() and view.should_update():
                views.append(view)

        return views