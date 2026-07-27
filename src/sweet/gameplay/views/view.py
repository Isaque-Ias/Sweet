import glm
from enum import Enum, auto
from abc import ABC
from ...core import system

class UpdatePolicy(Enum):
    EVERY_FRAME = auto()
    EVERY_N_TICKS = auto()
    ON_DEMAND = auto()
    ONCE = auto()

class Target(ABC):
    pass

class View:
    def __init__(self, update_policy: UpdatePolicy = UpdatePolicy.ON_DEMAND) -> None:
        self.update_policy = update_policy
        self._demanding: bool = False
        self._view: glm.mat4
        self._projection: glm.mat4

        self._active: bool = False
        self._target: Target | None = None
        self._updated: bool = False

        self._tick: int = 0
        self._total_ticks: int = 0

        ViewManager.add_view(self)

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

    @property
    def update_policy(self):
        return self._update_policy
    
    @update_policy.setter
    def update_policy(self, policy: UpdatePolicy, tick: int | None = None):
        self._update_policy: UpdatePolicy = policy
        if policy == UpdatePolicy.ONCE:
            self._updated = False
            self.add_demand()
            self._updated = True

        elif policy == UpdatePolicy.EVERY_N_TICKS:
            if tick is None or tick <= 0:
                tick = 1

            self._total_ticks = tick
            self._tick = 0

    def tick(self):
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._demanding = ViewManager.add_demand(self)
            self._tick = 0

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def is_active(self):
        self._active = False

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

    def render(self):
        self.clear_demand()

    def clear_demand(self):
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

        cls._views.append(view)
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
            if view.update_policy == UpdatePolicy.EVERY_N_TICKS:
                views.append(view)

        return views

    @classmethod
    def get_current_views(cls) -> list["View"]:
        views: list["View"] = []
        for view in cls._views:
            if view.is_active() and view.should_update():
                views.append(view)

        return views